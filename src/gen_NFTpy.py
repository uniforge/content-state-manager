import json
import os
from pygltflib import GLTF2, BufferFormat, Image, ImageFormat
from pygltflib.utils import gltf2glb, ImageFormat, Image
from PIL import Image as pilImage

from cover_generation import (
    RAINBOW_COLORS,
    FOREGROUND_IMAGES,
    block_hash_to_cover,
    GOLDEN_COLORS,
    GOLDEN_IMAGE,
)

# Color Info
# White - Common
# Green - Uncommon
# Blue - Rare
# Purple - Epic
# Orange - Legendary
# Gold - Golden Ticket

WHITE = [1.0, 1.0, 1.0, 1]
GREEN = [0.1, 1.0, 0.1, 1]
BLUE = [0.015, 0.025, 0.050, 1]
PURPLE = [0.5, 0.0, 0.5, 1]
ORANGE = [1.0, 0.2, 0.0, 1]
GOLD = [0.6584, 0.4287, 0.0382, 1]

white_rough = 1.0
green_rough = 0.5
other_rough = 0.05


# im_card = pilImage.open("./cards/card_000000001.png")
# im_cover = pilImage.open("./covers/cover_000000001.png")
# im_card.resize((576, 576), pilImage.NEAREST).save("newcard.png")
# im_cover.resize((576, 576), pilImage.NEAREST).save("newcover.png")


def resize_art(cover, card):
    # cover is expected to be a python image library IMAGE object already, since the cover gen was called prior
    # Card is only the filepath
    # Output will be temporary files newcover.png and newcard.png
    cover.resize((576, 576), pilImage.NEAREST).save("newcover.png")
    im_card = pilImage.open(card)
    im_card.resize((576, 576), pilImage.NEAREST).save("newcard.png")


ex_hash = "DT3oHwZcaLpLBDN8FiHZ87c9DZXYGvw1iK2qkkq51uaC"

# cover = block_hash_to_cover(ex_hash, GOLDEN_COLORS, GOLDEN_IMAGE)
# cover.save("goldenticket.png")
# cover2 = block_hash_to_cover(ex_hash, RAINBOW_COLORS, FOREGROUND_IMAGES)
# cover2.save("testcover.png")

# input_dir = "./testset/"
# output_dir = "./GLB/"
dirname = os.path.dirname(__file__)
input_dir = os.path.join(dirname, "testset")
output_dir = os.path.join(dirname, "GLB")
input_GLB = os.path.join(dirname, "Solset3D_base.gltf")

os.makedirs(output_dir, exist_ok=True)

input_fns = os.listdir(input_dir)

possible_tokens = []

for fn in input_fns:
    src = os.path.join(input_dir, fn)

    if os.path.splitext(src)[-1] == ".png":
        pass
    elif os.path.splitext(src)[-1] == ".json":
        dest = os.path.join(output_dir, fn)
        with open(src, "r") as input_file:
            metadata = json.load(input_file)
            print(metadata["level"])

            # generate the cover art
            # function for calling cover art
            if metadata["level"] == "golden":
                cover = block_hash_to_cover(ex_hash, GOLDEN_COLORS, GOLDEN_IMAGE)
            else:
                cover = block_hash_to_cover(ex_hash, RAINBOW_COLORS, FOREGROUND_IMAGES)

            # resize the cover and card for the GLB file
            # resize function input cover and card, output cover and card at 576X576
            # does this make sense to do this as a seperate function since I'm not passing image objects, I need PNG files saved so no return
            fn_card = "{}_{:09d}.png".format("insert", metadata["id"])
            print(fn_card)
            card_dirfn = os.path.join(input_dir, fn_card)
            print(card_dirfn)
            # cover.resize((576, 576), pilImage.NEAREST).save("newcover.png")
            # im_card = pilImage.open(card)
            # im_card.resize((576, 576), pilImage.NEAREST).save("newcard.png")
            resize_art(cover, card_dirfn)

            # Getting frustrated with os here, have to explicilty define the path to the newcard and newover png files
            # dirname = os.path.dirname(__file__)
            newcard_fn = os.path.join(dirname, "newcard.png")
            newcover_fn = os.path.join(dirname, "newcover.png")
            # create the GLB
            gltf = GLTF2().load(input_GLB)
            newimagecard = Image()
            newimagecard.uri = newcard_fn
            gltf.images[0] = newimagecard
            newimagecover = Image()
            newimagecover.uri = newcover_fn
            gltf.images[1] = newimagecover
            gltf.convert_images(ImageFormat.DATAURI)

            if metadata["level"] == "common":
                gltf.materials[3].pbrMetallicRoughness.baseColorFactor = WHITE
                gltf.materials[3].pbrMetallicRoughness.roughnessFactor = white_rough
            elif metadata["level"] == "uncommon":
                gltf.materials[3].pbrMetallicRoughness.baseColorFactor = GREEN
                gltf.materials[3].pbrMetallicRoughness.roughnessFactor = green_rough
            elif metadata["level"] == "rare":
                gltf.materials[3].pbrMetallicRoughness.baseColorFactor = BLUE
                gltf.materials[3].pbrMetallicRoughness.roughnessFactor = other_rough
            elif metadata["level"] == "epic":
                gltf.materials[3].pbrMetallicRoughness.baseColorFactor = PURPLE
                gltf.materials[3].pbrMetallicRoughness.roughnessFactor = other_rough
            elif metadata["level"] == "legendary":
                gltf.materials[3].pbrMetallicRoughness.baseColorFactor = ORANGE
                gltf.materials[3].pbrMetallicRoughness.roughnessFactor = other_rough
            elif metadata["level"] == "golden":
                gltf.materials[3].pbrMetallicRoughness.baseColorFactor = GOLD
                gltf.materials[3].pbrMetallicRoughness.roughnessFactor = other_rough

            fn_glb = "{}_{:09d}.glb".format("solset3d", metadata["id"])
            glb_dirfn = os.path.join(output_dir, fn_glb)
            gltf.save(glb_dirfn)


# print(data['images'][0]['uri'])

# newJson = json.dumps(data)
# newFile = open("newgltf.gltf", "w")
# newFile.write(newJson)
# newFile.close()
# print("now GLTF stuff")
# gltf = GLTF2().load("SolsetCard3D_8_5obj_5.gltf")
# # glb = GLTF2().load_binary("Solset3D_000000001.glb")
# print(gltf.images[1].uri)
# # print(glb.images[0])
# newimage = Image()
# newimage.uri = "newcard.png"
# gltf.images[0] = newimage
# newimage2 = Image()
# newimage2.uri = "newcover.png"
# gltf.images[1] = newimage2
# gltf.convert_images(ImageFormat.DATAURI)

# print(gltf.materials[3].pbrMetallicRoughness.baseColorFactor)

# gltf.save("8_5_BrendansBlue.glb")


## color info
# GOLD D4AF37
# "baseColorFactor": [
#           0.6584,
#           0.4287,
#           0.0382,
#           1
#         ],

# PURPLE 800080
# "baseColorFactor": [
#           0.5,
#           0.0,
#           0.5,
#           1
#         ],

# BLUE 0000FF
# "baseColorFactor": [
#           0.0,
#           0.0,
#           1.0,
#           1
#         ],

# Green 00FF00
# "baseColorFactor": [
#           0.0,
#           1.0,
#           0.0,
#           1
#         ],
