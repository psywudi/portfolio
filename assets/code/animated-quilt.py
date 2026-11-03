#################################################
# SP26_VFX705_01_Siyuan_Pang_P02_Animated Pixel Art_FINAL_v01.py
# Description: Animated Pixel Art
# By: Siyuan Pang
# Created: 28-April-2026
################################################

##########################################################################################
################ PUT THIS AT THE TOP OF ANY CODE YOU'RE WRITING FOR MAYA  ################
##########################################################################################
try:
    import maya.cmds as cmds
    IN_MAYA = True
except ImportError:
    IN_MAYA = False

    class MockCmds:
        def __getattr__(self, name):
            def mock(*args, **kwargs):
                print(f"[MOCK] cmds.{name}({args}, {kwargs})")
                return ["mock_result"]
            return mock

    cmds = MockCmds()
##########################################################################################
##########################################################################################
##########################################################################################


# 1. Read flat Piskel .c pixel lists.
# 2. Organize pixels into a frame dictionary: {frame_number: pixel_list}.
# 3. Create one subdivided polygon plane per animation frame.
# 4. Assign shaders per face with nested row / column loops.
# 5. Use visibility keyframes to switch animation frames.


import os
import re


##########################################################################################
# BASIC SETTINGS
##########################################################################################

PFX = "SP_P02_"

ROOT_GROUP = PFX + "AnimatedPixelQuilt_grp"
QUILT_GROUP = PFX + "Quilt_grp"

TILE_SIZE = 32
QUILT_SIZE = 5
PIXEL_SIZE = 1.0

MAYA_FPS = 24
PISKEL_FPS = 4
FRAME_HOLD = MAYA_FPS // PISKEL_FPS

try:
    SCRIPT_FOLDER = os.path.dirname(os.path.abspath(__file__))
except NameError:
    SCRIPT_FOLDER = r"C:\Users\Administrator\Desktop\Third Semester\705\02"

# The five .c files are in the same folder as this Python script.
DATA_FOLDER = SCRIPT_FOLDER

# Save each animation name with its .c file path.
C_FILES = {
    "crown": os.path.join(DATA_FOLDER, "Crown prince anime.c"),
    "hunter": os.path.join(DATA_FOLDER, "hunter.c"),
    "robot": os.path.join(DATA_FOLDER, "robot anime.c"),
    "undead": os.path.join(DATA_FOLDER, "Undead.c"),
    "warrior": os.path.join(DATA_FOLDER, "warrior.c"),
}

TILE_ORDER = ["crown", "hunter", "robot", "undead", "warrior"]
# The arrangement of the 5x5 quilt is consistent with the requirements of Project 01.
QUILT_PATTERN = [
    [0, 1, 2, 3, 4],
    [4, 0, 1, 2, 3],
    [3, 4, 0, 1, 2],
    [2, 3, 4, 0, 1],
    [1, 2, 3, 4, 0],
]


##########################################################################################
# CLEANUP
##########################################################################################

def cleanup_scene():
    # Delete only old objects, shaders, and groups made by this script.
    old_nodes = cmds.ls(PFX + "*") or []

    if old_nodes:
        cmds.delete(old_nodes)


##########################################################################################
# PARSE PISKEL C FILES
##########################################################################################

def find_define_number(file_text, define_word):
    # Find a number from a Piskel #define line.
    pattern = r"#define\s+.*" + define_word + r"\s+(\d+)"
    result = re.search(pattern, file_text)
    return int(result.group(1))


def organize_pixels_into_frames(all_pixels, width, height, frame_count):
    # Turn one long flat pixel list into a dictionary of frames.
    #
    # My image is 32x32, so:
    # The second frame covers indices 1024 - 2047.
    # The third frame covers indices 2048 - 3071.
    # The fourth frame covers indices 3072 - 4095.
    pixels_per_frame = width * height  # 32 x 32 = 1024 pixels per frame
    frames = {}

    for frame_num in range(frame_count):
        start = frame_num * pixels_per_frame
        end = start + pixels_per_frame
        frames[frame_num] = all_pixels[start:end]

    return frames


def read_piskel_c_file(file_path):
    # Read one Piskel .c file and return one animation data dictionary.
    file_text = open(file_path, "r", encoding="utf-8").read()
    # Read the frame count, width, and height from the .c file.
    frame_count = find_define_number(file_text, "FRAME_COUNT")
    width = find_define_number(file_text, "FRAME_WIDTH")
    height = find_define_number(file_text, "FRAME_HEIGHT")
    # Find all Piskel hex color values, such as 0xff000000.
    all_pixels = re.findall(r"0x[0-9a-fA-F]{8}", file_text)
    frames = organize_pixels_into_frames(all_pixels, width, height, frame_count)

    animation_data = {
        "frame_count": frame_count,
        "width": width,
        "height": height,
        "frames": frames,
    }

    return animation_data


def read_all_animations():
    animations = {}

    for tile_name in TILE_ORDER:
        c_file_path = C_FILES[tile_name]
        animation_data = read_piskel_c_file(c_file_path)
        animations[tile_name] = animation_data

    return animations



# ==============================================================================
# COLOR AND SHADER FUNCTIONS
# ==============================================================================

def hex_to_rgb_float(hex_color):
    # Convert Piskel 0xAABBGGRR color into Maya RGB float color.
    
    color_number = int(hex_color, 16)

    alpha = (color_number >> 24) & 255
    blue = (color_number >> 16) & 255
    green = (color_number >> 8) & 255
    red = color_number & 255

    if alpha == 0:
        red = 255
        green = 255
        blue = 255

    red = red / 255.0
    green = green / 255.0
    blue = blue / 255.0

    return (red, green, blue)


def collect_color_palette(animations):
    # Use a set to collect every unique color from all animations.
    color_palette = set()

    for tile_name in animations:
        frames = animations[tile_name]["frames"]

        for frame_num in frames:
            pixels = frames[frame_num]

            for hex_color in pixels:
                color_palette.add(hex_color)

    return color_palette


def make_one_shader(hex_color):
    # Create one shader for one unique color.
    clean_hex = hex_color.replace("0x", "")
    shader_name = PFX + "color_" + clean_hex + "_MAT"
    shading_group_name = PFX + "color_" + clean_hex + "_SG"

    rgb = hex_to_rgb_float(hex_color)

    shader = cmds.shadingNode("aiFlat", asShader=True, name=shader_name)
    cmds.setAttr(shader + ".color", rgb[0], rgb[1], rgb[2], type="double3")

    shading_group = cmds.sets(
        renderable=True,
        noSurfaceShader=True,
        empty=True,
        name=shading_group_name,
    )
    cmds.connectAttr(shader + ".outColor", shading_group + ".surfaceShader", force=True)

    return shading_group


def make_all_shaders(color_palette):
    # Make a dictionary: hex color -> Maya shading group.
    color_to_shader = {}

    for hex_color in color_palette:
        color_to_shader[hex_color] = make_one_shader(hex_color)

    return color_to_shader


# ==============================================================================
# MAYA PLANE AND FACE ASSIGNMENT
# ==============================================================================

def get_tile_position(quilt_row, quilt_col):
    # Calculate the x and y position for one tile in the 5x5 quilt.
    full_quilt_size = TILE_SIZE * QUILT_SIZE * PIXEL_SIZE
    half_quilt_size = full_quilt_size / 2.0

    x_pos = quilt_col * TILE_SIZE * PIXEL_SIZE
    x_pos = x_pos + (TILE_SIZE * PIXEL_SIZE / 2.0)
    x_pos = x_pos - half_quilt_size

    y_pos = half_quilt_size
    y_pos = y_pos - quilt_row * TILE_SIZE * PIXEL_SIZE
    y_pos = y_pos - (TILE_SIZE * PIXEL_SIZE / 2.0)

    return x_pos, y_pos


def assign_pixels_to_faces(plane_name, pixels, width, height, color_to_shader):
    # Assign one shader to each face.
    #
    # pixel_index reads the Piskel list in normal top-to-bottom order.
    # face_id is flipped because this Maya plane's face order is bottom-to-top.
    for row in range(height):
        for col in range(width):
            pixel_index = (row * width) + col
            hex_color = pixels[pixel_index]

            flipped_row = height - 1 - row
            face_id = (flipped_row * width) + col

            face_name = plane_name + ".f[" + str(face_id) + "]"
            cmds.sets(face_name, edit=True, forceElement=color_to_shader[hex_color])


def create_frame_plane(tile_name, quilt_row, quilt_col, frame_num, animation_data, color_to_shader, parent_group):
    # Create one plane for one frame of one tile.
    width = animation_data["width"]
    height = animation_data["height"]
    pixels = animation_data["frames"][frame_num]

    plane_name = (
        PFX + tile_name +
        "_tile_" + str(quilt_row) + "_" + str(quilt_col) +
        "_frame_" + str(frame_num)
    )

    plane = cmds.polyPlane(
        width=width * PIXEL_SIZE,
        height=height * PIXEL_SIZE,
        subdivisionsX=width,
        subdivisionsY=height,
        axis=(0, 0, 1),
        constructionHistory=False,
        name=plane_name,
    )[0]

    x_pos, y_pos = get_tile_position(quilt_row, quilt_col)
    cmds.move(x_pos, y_pos, 0, plane)
    cmds.parent(plane, parent_group)

    assign_pixels_to_faces(plane, pixels, width, height, color_to_shader)

    return plane


# ==============================================================================
# BUILD TILE AND QUILT
# ==============================================================================

def build_one_tile(tile_name, quilt_row, quilt_col, animation_data, color_to_shader, quilt_group):
    # Build all frame planes for one animated tile.
    tile_group_name = PFX + tile_name + "_tile_" + str(quilt_row) + "_" + str(quilt_col) + "_grp"
    tile_group = cmds.group(empty=True, name=tile_group_name, parent=quilt_group)

    frame_count = animation_data["frame_count"]
    frame_plane_names = []

    for frame_num in range(frame_count):
        frame_group_name = tile_group_name + "_frame_" + str(frame_num) + "_grp"
        frame_group = cmds.group(empty=True, name=frame_group_name, parent=tile_group)

        plane = create_frame_plane(
            tile_name,
            quilt_row,
            quilt_col,
            frame_num,
            animation_data,
            color_to_shader,
            frame_group,
        )

        frame_plane_names.append(plane)
        set_visibility_keyframes(frame_group, frame_num, frame_count)

    tile_data = {
        "tile_name": tile_name,
        "quilt_row": quilt_row,
        "quilt_col": quilt_col,
        "frame_plane_names": frame_plane_names,
        "tile_group": tile_group,
    }

    return tile_data


def build_quilt(animations, color_to_shader):
    # Build the full 5x5 animated quilt.
    root_group = cmds.group(empty=True, name=ROOT_GROUP)
    quilt_group = cmds.group(empty=True, name=QUILT_GROUP, parent=root_group)

    all_tiles = []

    for quilt_row in range(QUILT_SIZE):
        for quilt_col in range(QUILT_SIZE):
            tile_index = QUILT_PATTERN[quilt_row][quilt_col]
            tile_name = TILE_ORDER[tile_index]
            animation_data = animations[tile_name]

            tile_data = build_one_tile(
                tile_name,
                quilt_row,
                quilt_col,
                animation_data,
                color_to_shader,
                quilt_group,
            )

            all_tiles.append(tile_data)

    return all_tiles


# ==============================================================================
# KEYFRAME FUNCTIONS
# ==============================================================================

def set_visibility_keyframes(frame_group, frame_num, frame_count):
    # Show one frame group only at its own animation frame.
    for loop_frame in range(frame_count + 1):
        current_frame = loop_frame % frame_count
        maya_frame = 1 + (loop_frame * FRAME_HOLD)

        if current_frame == frame_num:
            visible_value = 1
        else:
            visible_value = 0

        cmds.setKeyframe(
            frame_group,
            value=visible_value,
            attribute="visibility",
            time=maya_frame,
        )

    cmds.keyTangent(frame_group, attribute="visibility", inTangentType="stepnext", outTangentType="stepnext")


def set_timeline(animations):
    # Set the Maya timeline based on the longest animation.
    longest_frame_count = 0

    for tile_name in animations:
        frame_count = animations[tile_name]["frame_count"]

        if frame_count > longest_frame_count:
            longest_frame_count = frame_count

    end_frame = longest_frame_count * FRAME_HOLD

    cmds.playbackOptions(minTime=1, maxTime=end_frame)
    cmds.currentTime(1)


# ==============================================================================
# MAIN FUNCTION
# ==============================================================================

def main():
    # Run the script in order.
    cleanup_scene()

    animations = read_all_animations()
    color_palette = collect_color_palette(animations)
    color_to_shader = make_all_shaders(color_palette)

    build_quilt(animations, color_to_shader)
    set_timeline(animations)

    print("Finished building the sorted animated pixel quilt.")


main()
