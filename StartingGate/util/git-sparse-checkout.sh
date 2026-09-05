#! /usr/bin/bash

git clone --no-checkout https://github.com/tquiggle/Diecast-Remote-Raceway.git
cd Diecast-Remote-Raceway
git sparse-checkout init --cone
git sparse-checkout set StartingGate
git checkout
