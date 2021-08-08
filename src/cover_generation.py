import base58

from PIL import Image, ImageDraw

RAINBOW_COLORS = [
    "#EF4123",
    "#F6821E",
    "#FFC40E",
    "#22B34A",
    "#008AD2",
    "#7E68B0",
]
GOLDEN_COLORS = [
    "#DAA520",
    "#D4AF37",
    "#E5C063",
    "#EDD290",
]
# had to modify path with ./ for runnign locally
# fg_images = {
#     "./images/Anvil.png": 40,
#     "./images/Hammer.png": 30,
#     "./images/BchsmObj0.png": 20,
#     "./images/sglasses3.png": 10,
# }

# had to modify path with ./ for runnign locally
fg_images = {
    "C:/Users/ograd/Projects/Uniforge/content-state-manager/src/images/Anvil.png": 40,
    "C:/Users/ograd/Projects/Uniforge/content-state-manager/src/images/Hammer.png": 30,
    "C:/Users/ograd/Projects/Uniforge/content-state-manager/src/images/BchsmObj0.png": 20,
    "C:/Users/ograd/Projects/Uniforge/content-state-manager/src/images/sglasses3.png": 10,
}


FOREGROUND_IMAGES = [[Image.open(fn)] * n for fn, n in fg_images.items()]
FOREGROUND_IMAGES = [img for img_list in FOREGROUND_IMAGES for img in img_list]
# GOLDEN_IMAGE = Image.open("images/BchsmObj2.png")
GOLDEN_IMAGE = Image.open(
    "C:/Users/ograd/Projects/Uniforge/content-state-manager/src/images/BchsmObj2.png"
)


def _block_hash_to_bit_stream(block_hash):
    block_bytes = base58.b58decode(block_hash)
    return "".join("{:08d}".format(int(bin(byte)[2:])) for byte in block_bytes)


def _block_hash_to_ints(block_hash, size):
    width = len(bin(size).lstrip("0b"))

    bit_stream = _block_hash_to_bit_stream(block_hash)

    i = 0
    values = []
    while i * width < len(bit_stream):
        byte_slice = bit_stream[i * width : (i + 1) * width]
        values.append(int(byte_slice, base=2) % size)
        i += 1

    return values


def _block_hash_to_colors(block_hash, colors):
    values = _block_hash_to_ints(block_hash, len(colors))

    return [colors[i] for i in values]


def _get_background(size, block_size, colors, alpha):
    assert (
        size % block_size == 0
    ), "Size {} is not an integer multiple of block size {}".format(size, block_size)
    n_blocks_per_size = size // block_size

    bg = Image.new("RGB", (size, size))
    draw = ImageDraw.Draw(bg, "RGBA")

    idx_color = 0

    for i in range(n_blocks_per_size):
        for j in range(n_blocks_per_size):
            upper_left = (i * block_size, j * block_size)
            lower_right = (upper_left[0] + block_size, upper_left[1] + block_size)
            draw.rectangle((upper_left, lower_right), fill=colors[idx_color])
            idx_color += 1

    draw.rectangle(((0, 0), (size, size)), fill=(255, 255, 255, int(alpha * 255)))

    return bg


def _get_placeholder(foreground_object, background_colors, alpha=0.7):
    assert (
        foreground_object.size[0] == foreground_object.size[1]
    ), "{} is not square".format(foreground_object.filename)

    bg_size = foreground_object.size[0] + 16
    fg_shift = 8

    bg = _get_background(48, 6, background_colors, alpha)
    bg.paste(foreground_object, (fg_shift, fg_shift), mask=foreground_object)

    return bg


def block_hash_to_cover(block_hash, colors, fg_images):
    # Hash to int
    block_hash_int = int.from_bytes(base58.b58decode(block_hash), "little")

    # Convert hash to colors
    block_colors = _block_hash_to_colors(block_hash, colors)

    # Convert hash to foreground object
    try:
        fg_obj = fg_images[block_hash_int % len(fg_images)]
    except:
        fg_obj = fg_images  # for the golden ticket fg_images is just a single image option so len() cannot be called

    return _get_placeholder(fg_obj, block_colors)
