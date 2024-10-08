# bancouver40

A 4x10 CFX spaced low-profile mechanical keyboard.

<image src="https://github.com/ChrisChrisLoLo/bancouver40/blob/main/images/PXL_20221205_015210392-01.jpeg" width="700"/>

Uncompromisingly small. Unabashedly uwu.

Also contains the source code for the 4x12 minipeg48 and the 4x4 kowgary16.

<image src="https://github.com/ChrisChrisLoLo/bancouver40/blob/main/images/PXL_20231022_023334208.jpg" width="700"/>

## Note
This keyboard works exclusively with CFX keycaps due to its tight spacing.

## Status
v0.0 PCBs confirmed to be working and should be good to be produced.

## About
This keyboard is a 4x10 ortholinear keyboard with one of the smallest possible footprints. By using Chosfox's 16.5x16.5mm CFX keycap, this keyboard is more compact than a typical choc spaced keyboard. Combined with the integrated ATMega32U4 makes this one of the smallest mechanical keyboards possible. Uses kailh choc hotswap sockets.

This keyboard also has the design files needed to order your own accompanying 3D-printed/Aluminum CNC case!

<image src="https://github.com/ChrisChrisLoLo/bancouver40/blob/main/images/PXL_20221205_012951007-01.jpeg" width="500"/>

## Case 
All of the case files you need can be found in the `case` directory.

## PCB
You can find the PCB source files in the `pcb` folder. The BOM files can be found in this folder.

## Directory Structure
- `case`
    You can find the files you need in this folder to print out a case for the keyboard
- `drafts`
    Stores any KLE or intermediate information used in making the case
- `firmware`
    Used to store any firmware relating to the keyboard. You should be able to find source files in my QMK fork
- `outlines`
    Outlines used to create the case and pcb
- `pcb`
    Kicad project relating to the project
   
## BOM
- 1 Assembled PCB (PCB BOM file can be found in `pcb` folder, minus the kailh hotswap sockets)
- 1 Aluminum CNC case or 3DP case (note that the 3DP threads can wear out, though I haven't has a problem with them yet)
- 6 4mm M2 screws (go for flathead for a flush fit, though other head types should also work)
- 4 1-3mm bumpons (something like Sj5302 is a good place to start)
- (optional) lasercut PE sheet for the bottom. Outline files can be in the `outlines` folder

Additionally, you should need
- 40 (plus spare) kailh choc switches. Avoid Red/White/Brown switches as they can be pretty rattly. Pro Red/Silver/Sunset switches are good places to start.
- 40 (plus spare) 1u CFX keycaps

<image src="https://github.com/ChrisChrisLoLo/bancouver40/blob/main/images/PXL_20221205_012230895-01.jpeg" width="500"/>

## Assembly
- All PCB components are SMD, and many of them are fairly small; PCBA services like PCBWay is highly recommended. BOM and centroid files in source files 
- Fairly straightforward with an assembled PCB; screw the PCB to the case using the M2 Screws. Add bumpons to case.

## Firmware
You can find a pre-compiled firmware file in the firmware folder of this repository. If you wish to customize the layout yourself, you can find the source code of the firmware here: https://github.com/ChrisChrisLoLo/qmk_firmware/blob/bancouver40/keyboards/sporewoh/bancouver40/readme.md.

## Acknowledgements
Big thank you to [PCBWay](https://www.pcbway.com/) for sponsoring this by manufacturing the red aluminum case for me! The anodization coloring is stunning, and I'm impressed by the CNC case quality as a whole. PCBWay offers very reasonable prices for even singluar one-off case manufactures, so I recommend them if you want to look into ordering an aluminum case for yourself or for cnc prototyping as a whole! Case files, as well as a detailed design drawing (required for screw tappings) can be found in the case folder.

Also a big thank you to [Chosfox](https://chosfox.com/) for providing their [Chocfox CFX keycaps](https://chosfox.com/collections/low-profile-keycaps/products/chocfox-cfx-choc-keycaps) as well as choc switches and hotswap sockets! I'm really excited that there's more offerings in the choc keycap space, and I'm a big fan of their square, spherical indented shape. They're very aethetically pleasing (i.e. very small and cute) and comfortable to type on. Chosfox is also continuing to invest in this line of products (1.25u+ keycaps, legends), so I highly recommend trying them out for any choc related keyboard you may have, bancouver40 or not!
