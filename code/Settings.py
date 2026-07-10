PIXELS_PER_UNIT: int = 40
SCREEN_SIZE: int = int(PIXELS_PER_UNIT * 19)

center: int = SCREEN_SIZE // 2
neg: int = center - 9 * PIXELS_PER_UNIT
pos: int = center + 9 * PIXELS_PER_UNIT
u = PIXELS_PER_UNIT  # shorthand
c = center  # shorthand

if __name__ == "__main__":
    print(
        "You are running Settings.py directly. This file is meant to be"
        " imported as a module, so there is no code to run here."
    )
