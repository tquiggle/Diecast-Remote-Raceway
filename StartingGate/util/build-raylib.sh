#! /usr/bin/bash

#
# Shell script to bouild and install the DRM version of raylib 5
#

num_cpus=$(nproc)

cd
git clone https://github.com/raysan5/raylib.git --branch 5.0 --single-branch
cd raylib
mkdir build
cd build
cmake -DPLATFORM="DRM" -DBUILD_EXAMPLES=OFF -DCUSTOMIZE_BUILD=ON -DSUPPORT_FILEFORMAT_JPG=ON -DSUPPORT_FILEFORMAT_FLAC=ON -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX:PATH=/usr ..
make -j $num_cpus
sudo make install

