#!/usr/bin/env python3
"""Generate Treeplacer sapling_overrides from Geophilic's own worldgen.

Run from the repo root:  python3 .dev/treeplacer_overrides.py

Reads the overlay-resolved worldgen data, expands each biome's tree
random_selector into concrete (configured_feature, probability) pairs, splits
those pairs by which sapling grows them, and writes one override file per
sapling. Regenerate after changing any */trees placed feature.
"""

import json
import glob
import os
import sys

OUT_ROOT = 'data/geophilic/sapling_overrides'

ALL_BIOMES = 'treeplacer:all_biomes'

# Treeplacer runs its own 2x2 check before vanilla's and, finding no mega entry,
# falls through to the single override instead of letting vanilla place a mega
# tree. So every biome with a single override needs a mega counterpart; these are
# the trees used when Geophilic generates no mega of its own there.
MEGA_FALLBACK = {
    # TreeGrower.SPRUCE carries secondaryChance 0.5, so vanilla flips a coin.
    'spruce_sapling': [('minecraft:mega_spruce', 50), ('minecraft:mega_pine', 50)],
    'dark_oak_sapling': [('minecraft:dark_oak', 100)],
    # TreeGrower.PALE_OAK grows PALE_OAK_BONEMEAL, not the worldgen pale_oak.
    'pale_oak_sapling': [('minecraft:pale_oak_bonemeal', 100)],
}

# Vanilla grows these only as a 2x2, so Geophilic's 1x1 variants are the sole way
# to grow one from a lone sapling and are offered in every biome.
SINGLE_ONLY_ANYWHERE = ('dark_oak_sapling', 'pale_oak_sapling')

# Never reachable from a sapling, whatever the pools say.
SAPLING_EXCLUDED = {
    # Vanilla routes sapling growth to PALE_OAK_BONEMEAL specifically to keep
    # creaking hearts out of player-grown trees; honour that even though
    # worldgen has one.
    'geophilic:tree/pale_oak/creaking',
    # Azaleas are minecraft:tree features built on oak logs, so classify reads
    # them as oak. They grow from an azalea bush, not an oak sapling.
    'geophilic:bush/azalea',
    'geophilic:biome_specific/cherry_grove/azalea_bush',
}

# The GiantTrunkPlacer subclasses, i.e. the trunks needing a 2x2 sapling square.
# A feature using one is only reachable from a mega override, never a single.
MEGA_TRUNKS = {
    'minecraft:giant_trunk_placer',
    'minecraft:dark_oak_trunk_placer',
    'minecraft:mega_jungle_trunk_placer',
    'minecraft:pale_oak_trunk_placer',
}

# Vanilla features have no JSON here, so what classify() would otherwise read
# from data is stated instead. Doubles as the allowlist: an id absent from this
# map is dropped rather than emitted, which matters because Treeplacer resolves
# ids with getOrThrow and so dies at growth time, not at load.
VANILLA_CF = {
    'minecraft:fancy_oak': ('oak_sapling', 'single'),
    'minecraft:pine': ('spruce_sapling', 'single'),
    'minecraft:jungle_tree': ('jungle_sapling', 'single'),
    'minecraft:mega_spruce': ('spruce_sapling', 'mega'),
    'minecraft:mega_pine': ('spruce_sapling', 'mega'),
    'minecraft:mega_jungle_tree': ('jungle_sapling', 'mega'),
}

CF_PREFIX = 'geophilic/worldgen/configured_feature/'
PF_PREFIX = 'geophilic/worldgen/placed_feature/'


def data_dirs():
    """The data dirs to layer for the pack's newest format, later ones winning.

    Both the format and the overlay list come from pack.mcmeta, so adding an
    overlay needs no edit here; hardcoding either would silently mirror the
    wrong worldgen once Geophilic moved on.
    """
    with open('pack.mcmeta') as fh:
        meta = json.load(fh)
    target = meta['pack']['max_format']
    dirs = ['data']
    for entry in meta.get('overlays', {}).get('entries', []):
        if entry['min_format'] <= target <= entry['max_format']:
            dirs.append(os.path.join(entry['directory'], 'data'))
    return dirs


def build_index():
    index = {}
    for base in data_dirs():
        for path in glob.glob(base + '/**/*.json', recursive=True):
            index[os.path.relpath(path, base)] = path
    return index


IDX = build_index()


def load(rel):
    with open(IDX[rel]) as fh:
        return json.load(fh)


def cf_rel(cf_id):
    return CF_PREFIX + cf_id.split(':', 1)[1] + '.json'


def pf_rel(pf_id):
    return PF_PREFIX + pf_id.split(':', 1)[1] + '.json'


def classify(cf_id):
    """(sapling, 'single'|'mega') for a growable feature, else None.

    Both facts come from the feature itself: the trunk block names the sapling
    and the trunk placer decides the footprint, so adding a tree needs no edit
    here. Anything that is not a minecraft:tree -- fallen logs, huge mushrooms
    -- grows from no sapling at all.
    """
    if cf_id in SAPLING_EXCLUDED:
        return None
    if not cf_id.startswith('geophilic:'):
        return VANILLA_CF.get(cf_id)
    rel = cf_rel(cf_id)
    if rel not in IDX:
        return None
    data = load(rel)
    if data['type'] != 'minecraft:tree':
        return None

    config = data['config']
    provider = config['trunk_provider']
    if provider['type'] != 'minecraft:simple_state_provider':
        raise SystemExit('%s: cannot name a sapling from trunk_provider %r'
                         % (cf_id, provider['type']))
    log = provider['state']['Name'].split(':', 1)[1]
    if not log.endswith('_log'):
        raise SystemExit('%s: unexpected trunk block %r' % (cf_id, log))

    kind = 'mega' if config['trunk_placer']['type'] in MEGA_TRUNKS else 'single'
    return log.removesuffix('_log') + '_sapling', kind


def expand_cf(node, weight):
    """Expand a *configured feature* reference into [(cf_id, probability), ...].

    A placed feature's top-level "feature" field is a configured-feature id,
    whereas the slots inside a random_selector are placed-feature ids. Mixing
    the two up silently drops whole biomes, so they get separate entry points.
    """
    if isinstance(node, str):
        return [(node, weight)]

    if isinstance(node, dict) and node.get('type') == 'minecraft:random_selector':
        config = node['config']
        out = []
        remaining = weight
        # Entries are tested in order and the first hit wins, so entry i only
        # fires when every earlier entry missed.
        for entry in config['features']:
            chance = entry['chance']
            out += expand_pf(entry['feature'], remaining * chance)
            remaining *= (1.0 - chance)
        out += expand_pf(config['default'], remaining)
        return out

    return []


def expand_pf(node, weight):
    """Expand a *placed feature* reference into [(cf_id, probability), ...]."""
    if isinstance(node, str):
        if node.startswith('geophilic:'):
            rel = pf_rel(node)
            return expand_cf(load(rel)['feature'], weight) if rel in IDX else []
        # Treeplacer resolves ids against CONFIGURED_FEATURE, so unwrap vanilla's
        # "_checked" placed features. Unknown ids fall out at classify().
        return [(node.removesuffix('_checked'), weight)]

    # Inline placed feature: {"feature": <cf ref>, "placement": [...]}
    if isinstance(node, dict) and 'feature' in node:
        return expand_cf(node['feature'], weight)

    return []


def to_weights(pairs):
    """Normalise probabilities to integers summing to 100."""
    total = sum(p for _, p in pairs)
    scaled = [(cf, max(1, round(p / total * 100))) for cf, p in pairs]
    drift = 100 - sum(w for _, w in scaled)
    if drift:
        top = max(range(len(scaled)), key=lambda i: scaled[i][1])
        scaled[top] = (scaled[top][0], scaled[top][1] + drift)
    return scaled


def collect():
    """Two maps of biome id -> sapling -> [(cf_id, weight)], for 1x1 and 2x2."""
    single, mega = {}, {}
    for rel in sorted(IDX):
        if not rel.startswith('minecraft/worldgen/biome/'):
            continue
        biome = 'minecraft:' + rel[len('minecraft/worldgen/biome/'):-len('.json')]
        steps = load(rel).get('features', [])
        pools = [pf for step in steps for pf in step
                 if pf.startswith('geophilic:') and pf.rsplit('/', 1)[-1].endswith('trees')]
        if not pools:
            continue

        merged = {}
        for pf in pools:
            for cf, prob in expand_cf(load(pf_rel(pf))['feature'], 1.0 / len(pools)):
                merged[cf] = merged.get(cf, 0.0) + prob

        buckets = {'single': {}, 'mega': {}}
        for cf, prob in merged.items():
            grown = classify(cf)
            if grown is None:
                continue
            sapling, kind = grown
            buckets[kind].setdefault(sapling, []).append((cf, prob))

        for kind, out in (('single', single), ('mega', mega)):
            for sapling, pairs in buckets[kind].items():
                # Strict Geophilic mirror: skip pools that add nothing of
                # Geophilic's. Mega pools are exempt because they exist to stop
                # the 2x2 fallthrough even when every option is vanilla.
                if kind == 'single' and not any(cf.startswith('geophilic:') for cf, _ in pairs):
                    continue
                pairs.sort(key=lambda kv: (-kv[1], kv[0]))
                out.setdefault(biome, {})[sapling] = to_weights(pairs)
    return single, mega


def pivot(data):
    """biome -> sapling -> entries  becomes  sapling -> biome -> entries"""
    out = {}
    for biome in sorted(data):
        for sapling, entries in data[biome].items():
            out.setdefault(sapling, {})[biome] = entries
    return out


def merge_biomes(by_biome):
    """Collapse one sapling's per-biome pools into a single everywhere-pool."""
    totals = {}
    for entries in by_biome.values():
        for cf, weight in entries:
            totals[cf] = totals.get(cf, 0.0) + weight
    pairs = sorted(totals.items(), key=lambda kv: (-kv[1], kv[0]))
    return to_weights(pairs)


def build(single_pools, mega_pools):
    single = pivot(single_pools)
    mega_geophilic = pivot(mega_pools)
    mega = {}

    for sapling, by_biome in single.items():
        if sapling not in MEGA_FALLBACK:
            continue
        for biome in by_biome:
            entries = mega_geophilic.get(sapling, {}).get(biome)
            mega.setdefault(sapling, {})[biome] = entries or list(MEGA_FALLBACK[sapling])

    for sapling in SINGLE_ONLY_ANYWHERE:
        if sapling not in single:
            continue
        single[sapling][ALL_BIOMES] = merge_biomes(single[sapling])
        mega.setdefault(sapling, {})[ALL_BIOMES] = list(MEGA_FALLBACK[sapling])

    return single, mega


def write(kind, per_sapling):
    out_dir = os.path.join(OUT_ROOT, kind, 'minecraft')
    os.makedirs(out_dir, exist_ok=True)
    for sapling in sorted(per_sapling):
        values = {}
        for biome in sorted(per_sapling[sapling]):
            entries = per_sapling[sapling][biome]
            if len(entries) == 1:
                values[biome] = entries[0][0]
            else:
                values[biome] = [{'feature': cf, 'weight': w} for cf, w in entries]
        path = os.path.join(out_dir, sapling + '.json')
        with open(path, 'w') as fh:
            json.dump({'replace': False, 'values': values}, fh, indent='\t')
            fh.write('\n')
        print('wrote %s (%d biomes)' % (path, len(values)))


def main():
    single, mega = build(*collect())
    results = (('single', single), ('mega', mega))

    if '--dry-run' in sys.argv:
        for kind, per_sapling in results:
            print('#', kind.upper())
            for sapling in sorted(per_sapling):
                print('==', sapling)
                for biome in sorted(per_sapling[sapling]):
                    pretty = ', '.join('%s=%d' % (cf.split(':', 1)[1], w)
                                       for cf, w in per_sapling[sapling][biome])
                    print('   %-34s %s' % (biome, pretty))
        return

    for kind, per_sapling in results:
        write(kind, per_sapling)


if __name__ == '__main__':
    main()
