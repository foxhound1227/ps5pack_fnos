# Bundled LZ4 profiles

`ampr_pack` TOML profiles that LZ4 Compression picks automatically. Each one is
matched to a game by Title ID or name, and the engine profiles also by the
game's file layout:

| Profile | Picked for | Tested on | Source |
|---|---|---|---|
| `astrobot.toml` | ASTRO BOT | ASTRO BOT (PPSA21567, 01.019.000) | [MkPFS.CSharp #5](https://github.com/danthespal/MkPFS.CSharp/issues/5) |
| `ufc6-PPSA23566.toml` | EA Sports UFC 6 | EA SPORTS UFC 6 (PPSA23566, 01.004.000) | [MkPFS.CSharp #2](https://github.com/danthespal/MkPFS.CSharp/issues/2) |
| `insomniac.toml` | Insomniac games (`toc`, `dag` and a `d/` folder at the top) | Marvel's Wolverine (PPSA03671, 01.001.005) | [MkPFS.CSharp #4](https://github.com/danthespal/MkPFS.CSharp/issues/4) |
| `unity.toml` | Unity games (`StreamingAssets` next to Unity's `Data` files) | God of War Sons of Sparta (PPSA28997, 01.008.001) | [MkPFS.CSharp #3](https://github.com/danthespal/MkPFS.CSharp/issues/3) |

The profiles were written and tested by danthespal and posted with
[MkPFS.CSharp](https://github.com/danthespal/MkPFS.CSharp) (GPL-3.0). They are
copied unchanged. `astrobot.toml` is the same file Lazy_AMPR ships.

Every profile keeps files it doesn't name loose, so a different game version
packs less but stays safe. To add one, drop the `.toml` here, add an entry to
`index.json` and rebuild.
