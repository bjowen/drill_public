#!/bin/bash
# by Ben Owen
# Install version of LALSuite needed for drill on Quanah.

# Setup libraries etc
module load gcc/10.1.0 fftw/3.3.9 gsl/2.7 python/3.8.3 py-numpy/1.19.0
export LD_LIBRARY_PATH=$FFTW_LIB:$GSL_LIB:$LD_LIBRARY_PATH
export LIBRARY_PATH=$FFTW_LIB:$GSL_LIB:$LIBRARY_PATH
export PKG_CONFIG_PATH=$FFTW_LIB/pkgconfig:$GSL_LIB/pkgconfig:$PKG_CONFIG_PATH
export CODE=$PWD
export CFLAGS="-O3 -Wno-error"
export PKG_CONFIG_PATH=$CODE/lib/pkgconfig:$PKG_CONFIG_PATH
export LDFLAGS=-L$CODE/lib

# Install Frame library if needed
if [ ! -d framelib-8.33 ]; then
    curl https://lappweb.in2p3.fr/virgo/FrameL/libframe-8.33.tar.gz | tar xzf -
    mv v8r33 framelib-8.33
    cd framelib-8.33
    autoreconf --install
    ./configure --prefix=$CODE
    make
    make install
    make distclean
    cd ..
fi

# Install lal if needed
if [ ! -d lal-6.22.0 ]; then
    curl https://software.igwn.org/sources/source/lalsuite/lal-6.22.0.tar.xz | tar xJf -
    cd lal-6.22.0
    ./configure --prefix=$CODE --disable-swig
    make
    make install
    . $CODE/etc/lal-user-env.sh
    make distclean
    cd ..
fi

# Install lalframe if needed
if [ ! -d lalframe-1.5.0 ]; then
    curl https://software.igwn.org/sources/source/lalsuite/lalframe-1.5.0.tar.xz | tar xJf -
    cd lalframe-1.5.0
    ./configure --prefix=$CODE --disable-swig
    make
    make install
    . $CODE/etc/lalframe-user-env.sh
    make distclean
    cd ..
fi

# Install lalpulsar if needed
if [ ! -d lalpulsar-1.18.2 ]; then
    curl https://software.igwn.org/sources/source/lalsuite/lalpulsar-1.18.2.tar.xz | tar xJf -
    cd lalpulsar-1.18.2
    ./configure --prefix=$CODE --disable-swig
    make
    make install
    . $CODE/etc/lalpulsar-user-env.sh
    make distclean
    cd ..
fi

# Install lalapps if needed
if [ ! -d lalapps-6.25.1 ]; then
    curl https://software.igwn.org/sources/source/lalsuite/lalapps-6.25.1.tar.xz | tar xJf -
    cd lalapps-6.25.1
    ./configure --prefix=$CODE --disable-lalmetaio --disable-lalburst --disable-lalinspiral --disable-lalsimulation --disable-lalinference
    make
    make install
    . $CODE/etc/lalapps-user-env.sh
    make distclean
    cd ..
fi
