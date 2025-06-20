# MTG experiments with satpy

1. download products with `eumdac` and unpack the zipfiles into a directory
2. `./mtg inventory {directory}` shows what datasets are available
3. `./mtg composites {directory}` shows what composites can be generated
4. `./mtg gen {directory} {compositename1} {compositename2}...` generates the named composites

Area can be selected with `mtg gen --area`.

Areas can be configured in `config/areas.yaml`.

New composites can be configured in `config/composites/fci.yaml` and
`config/enhancements/fci.yaml`.


## Notes

Both EO:EUM:DAT:0662 and EO:EUM:DAT:0665 product may be needed to enable all
possible composites.
