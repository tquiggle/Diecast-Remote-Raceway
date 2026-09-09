# Diecast Remote Raceway - Starting Gate - Software Build Instructions

The simplest way to get started is to download the latest release as a complete 
Raspberry Pi system image for either the Raspberry Pi Zero W or the Raspberry
Pi Zero 2W.  These are complete images that can be burned to a microSD card
using the [Raspberry Pi Imager](https://www.raspberrypi.com/software/) or
[Balena Etcher](https://etcher.balena.io/)

## Building From Scratch

### Install Raspberry PI OS

The DRR software writes directly to the framebuffer and does not need a desktop OS image.

I recommend you install via the [Raspberry Pi Imager](https://www.raspberrypi.com/software/). You will need a minimum 8GB microSDHC card.
Insert the card into an appropriate card reader on your computer.

Run the Raspberry Pi Imager and select your board.

1.  On the "Device" tab either the "Raspberry Pi Zero W" or "Raspberry Pi Zerro 2 W" depending in which board you are using.  Click Next.
1.  On the "OS" tab select "Raspberry Pi OS (other)" then either "Raspberry Pi OS Lite (32-bit)" for the Zero or "Raspberry Pi Os
Lite (65-bit) for the Zero 2 board.  Click Next.
1.  On the "Storage" tab select the appropriate option for the storage card you are initializing. Click Next.
1.  On "Customization -> Hostname" tab enter the hostname for your Starting Gate.  I use "drr". Click Next.
1.  On "Customization -> Localisation" Specify your Country's capital, your Timezone and Keyboard Layout. Click Next.
1.  On "Customization -> User" Select a Username and Password. The prebuilt image uses "drr" and "HotWheels".  Click Next.
1.  On "Customization -> WiFi" Select a SSID and Password. The prebuilt image skips this step.  Click Next
1.  On "Customization -> Remote Access" Toggle the Enable SSH on and select "Use Password Authentication".  Click Next.
1.  On "Customization -> Raspberry Pi Connect" Set the toggle to Off.  Click Next
1.  Click on "WRITE" to write the OS image to your SD card

Once your SD card is initialized insert it into your Raspberry Pi Zero.
You can either connect a keyboard and monitor or just SSH into the device
when it boots. Log in using the username and password you created when
running the Raspberry Pi Imager.

Once logged in, I strongly recommend you upgrade any packages:

```
sudo apt update
sudo apt upgrade
```

### Install Python 3 and the necessary libraries

1. Install the necessary prerequisites:

    ```bash
    sudo apt install --no-install-recommends -y cmake git python3 python3-setuptools python3-dev python3-gpiozero python3-pigpio python3-bluez python3-pip libegl1-mesa-dev libgbm-dev libgles2-mesa-dev libdrm-dev
    ```

### Download Starting Gate Software from GitHub

At present, all three components (Starting Gate, Finish Line, Coordinator) are located in the same GitHub repository. Perform a sparse checkout to obtain just the Starting Gate directory.

```bash
wget https://raw.githubusercontent.com/tquiggle/Diecast-Remote-Raceway/refs/heads/master/StartingGate/util/git-sparse-checkout.sh

chmod +x git-sparse-checkout.sh
./git-sparse-checkout.sh
```

or execute the following by hand:

```bash
git clone --no-checkout https://github.com/tquiggle/Diecast-Remote-Raceway.git
cd Diecast-Remote-Raceway
git sparse-checkout init --cone
git sparse-checkout set StartingGate
git checkout
```

### Build and install pigpiod

Sadly, pigpiod is no longer available as a package from the standard RPI
repository as it doesn't support the Raspberry Pi 5. You need to build
it from source.

1.  Build pigpiod from source

```bash
wget https://github.com/joan2937/pigpio/archive/refs/tags/v79.tar.gz
tar zxf v79.tar.gz
cd pigpio-79
make
sudo make install

```

1.  Have pigpiod start on every boot and start it now (without having to reboot)

    Run the pigpiod-service.sh utility from the  utils subdirectory

    ```bash
    sudo ~/Diecast-Remote-Raceway/StartingGate/util/pigpiod-service.sh
    ```

### Setup the Waveshare 1.3" LCD HAT

Raspberry OS Bookworm has native support for the st7799 display driver chip.  There is no need to follow the instructions from the [Waveshare
Wiki](https://www.waveshare.com/wiki/1.3inch_LCD_HAT). The shell script `setup-waveshare-1.3-HAT.sh` in the util subdirectory will perform all necessary changes to a base Raspberry OS system.

```
sudo ~/Diecast-Remote-Raceway/StartingGate/util/setup-waveshare-1.3-HAT.sh
```

### Build the DRM version of Raylib

This mostly follows the instructions at the [Python Bindings for Raylib 5.5](https://electronstudio.github.io/raylib-python-cffi/README.html) Github page for [Compile Raylib from source DRM mode](https://electronstudio.github.io/raylib-python-cffi/RPI.html#option-3-compile-raylib-from-source-drm-mode) for the Raspberry Pi.

1. Build a shared lib version of Raylib in DRM mode and install to /usr:

    ```
    ~/Diecast-Remote-Raceway/StartingGate/util/build-raylib.sh
    ```

    ```
    git clone https://github.com/raysan5/raylib.git --branch 5.5 --single-branch
    cd raylib
    mkdir build
    cd build
    cmake -DPLATFORM="DRM" -DBUILD_EXAMPLES=OFF -DCUSTOMIZE_BUILD=ON -DSUPPORT_FILEFORMAT_JPG=ON -DSUPPORT_FILEFORMAT_FLAC=ON -DCMAKE_BUILD_TYPE=Release -DBUILD_SHARED_LIBS=ON -DCMAKE_INSTALL_PREFIX:PATH=/usr ..
    make -j
    sudo make install
    ```

1. Then have pip compile and install the wheel for the python bindings:

    ```
    sudo python3 -m pip install --break-system-packages setuptools
    sudo python3 -m pip install --break-system-packages --no-cache-dir --no-binary raylib --upgrade --force-reinstall raylib==5.5.0.0
    ```

That's it, you sould be able to run the DRR python application.

