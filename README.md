# Satmaps

Satellite product generation using [satpy](https://github.com/pytroll/satpy).

## Usage

In the following usage examples, it is assumed that input data has been
downloaded in the `inputs/` directory.

### List available composites

You can use `satmaps composites -i inputs` to list all composites that can be
generated from the input data.

### List available areas

You can use `satmaps areas` to list all available areas.

### Rendering products

You can use `satmaps render -i inputs -o outputdir` to render all available
composites to products in the given output directory.

You can use `--flavour` to specify a flavour file to control the processing.

You can also append composite names to render only the given composites.

Composites already present in the output directory will not be generated again,
so it's possible to build the output product set incrementally.

### Running directly from the git checkout

Note that, when running from the git checkout, you need to use `python3 -m
satmaps` instead of `satmaps`.

## Configuration

Processing can be configured via the `recipes/` directory. It contains:

* `satpy/`: satpy configuration, such as area definitions and definitions of custom composites
* `flavours/`: named YAML files containing configuration of the generation run,
  such as area selection, or a selection of what composites should be generated

Satpy data is stored across runs in the `data/` directory.

New composites can be configured in `config/composites/` and
`config/enhancements/`: see `README.md` files in those directories.

## Performance

You can use the `DASK_NUM_WORKERS` environment variable to define the number of
worker threads for processing.

For more information, see: <https://satpy.readthedocs.io/en/stable/faq.html#why-is-satpy-slow-on-my-powerful-machine>

## System compatibility

The minimal target distribution is Rocky Linux 10.

Relevant dependencies are:

* Python 3.12
