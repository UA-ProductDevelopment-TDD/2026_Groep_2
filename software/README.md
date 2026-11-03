# Software

Firmware and code that drives the add-on.

Put here:

- Firmware for the robot and the add-on
- Scripts and tools that talk to the robot
- Tests
- Build and flash instructions

Document how to build, flash and run the code in this file as soon as there is something to run.

## Tests

### `tests/mlx90614_test`

Reads the DFRobot MLX90614 heat sensor over I2C (address 0x5A) and prints the ambient and object temperature every 500 ms. Tested on an Arduino UNO R4 Minima with a Grove Base Shield; the sensor goes in an I2C port.

```sh
arduino-cli core install arduino:renesas_uno
arduino-cli compile -u -p /dev/ttyACM0 --fqbn arduino:renesas_uno:minima software/tests/mlx90614_test
arduino-cli monitor -p /dev/ttyACM0 -c baudrate=115200
```

On Linux, uploading first needs USB permissions: run `post_install.sh` from the `renesas_uno` core folder once with `sudo`.
