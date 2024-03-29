# AYON USD

This is AYON Addon for support of [USD](https://github.com/PixarAnimationStudios/OpenUSD).

It helps to distribute USD binaries and related tools to artist workstations and
to configure its environment.

To define the sources of the USD binaries, edit the `create_package.py` file
and change the `DISTRIBUTE_SOURCE_URL` and `USD_SOURCES` as needed.

## Building the addon

Run:
```sh
python create_package.py
```
It will download usd zip files and put them in the `private` folder. Then it
will create a zip file with the addon.

You just need to upload that addon zip from the `package` directory to your
server and use it with your bundle.

## Building USD for Linux using Docker

There are tools that help building USD Framework using Docker (or Podman) in a
safe environment and with your choice of Python version, so you can get the
binaries as fast as possible (hardware dependant) and avoiding to "pollute"
your system.

It's based on the [Azure pipelines that Pixar](https://github.com/PixarAnimationStudios/OpenUSD/blob/release/azure-pipelines.yml) uses to run their
automated builds, with some added QoL, such as being able to define a
Python version.

### How to use

#### Linux

It builds USD with the following arguments: `--ptex --openvdb --openimageio --openimageio --alembic --hdf5`

Clone this repository in your computer and then simply run within:
  `podman build -t usd-linux:py37 -f linux-containerfile --build-arg PYTHON_VERSION="3.7"`

If not `PYTHON_VERSION` build arg is specified, it defaults to `3.9` (as per the VFX Platfrom Reference):
  `podman build -t usd-linux -f linux-containerfile`

This will take a while, so grab a cup of your favourite beverage, if all goes
well, you should have an image with `USD` built at the `/USD` folder, you can
now extract the contents by starting a container with said image, and then
copying the contents:

```
  # First spawn a container with the `usd-linux` image
  podman run -it --rm  usd-linux bash 
```

On **another** terminal:
  ```
  # List all the runnign containers
  podman ps | grep usd-linux
  # Note down the ${container-id} from the command above
  podman cp ${container-id}:/USD /path/in/your/host/USD
```

You should now have USD binaries in `/path/in/your/host/USD`, note that if you
are going to use any of the tools that require Python bindings you'll have to
match the Python version used at build time!

### Todo
 - [] Windows Dockerfile.
 - [] MacOs Dockerfile.
 - [] Allow passing USD build arguments.


