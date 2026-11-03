#################################################
# SP26_VFX705_01_Siyuan_Pang_P03_NewtonsCradle_Final_v01
# Description: Newton's Cradle
# By: Siyuan Pang
# Created: 12-May-2026
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

#######################################
# 1. Basic Settings
# 2. Materials
# 3. Modeling
# 4. Animation
# 5. Lighting Setup
# 6. Camera Setup
######################################

import math
import os
import maya.cmds as cmds


######################################
# 1. Basic Settings
######################################

PFX = "NewtonsCradle_"
OLD_PREFIX = "NC_WIP_"

HDRI_PATH = r"C:\Users\Administrator\Desktop\705newton\lebombo_4k.exr"
WOOD_TEXTURE_PATH = r"C:\Users\Administrator\Desktop\705newton\WoodBoardMaterial.png"
WALL_TEXTURE_PATH = r"C:\Users\Administrator\Desktop\705newton\WallMaterial.png"

BALL_COUNT = 5
BELL_RADIUS = 0.26
BELL_SPACING = BELL_RADIUS * 2.46
START_FRAME = 1
END_FRAME = 120

FULL_WIDTH = 1920
FULL_HEIGHT = 1080

FRAME_HALF_WIDTH = 2.65
FRONT_Z = 1.05
BACK_Z = -1.05
TOP_Y = 3.85

def clear_previous_build():
    if cmds.objExists(PFX + "*"):
        cmds.delete(PFX + "*")

    if cmds.objExists(OLD_PREFIX + "*"):
        cmds.delete(OLD_PREFIX + "*")


######################################
# 2. Materials
######################################

def make_shader(name, color, metalness=0.0, roughness=0.35):
    
    shader = cmds.shadingNode("aiStandardSurface", n=PFX + name, asShader=True)
    cmds.setAttr(shader + ".baseColor", color[0], color[1], color[2])
    cmds.setAttr(shader + ".metalness", metalness)
    cmds.setAttr(shader + ".specularRoughness", roughness)
    return shader




def make_texture_shader(name, texture_path, roughness=0.45):
    shader = make_shader(name, (1, 1, 1), roughness=roughness)
    image_node = cmds.shadingNode("aiImage", n=PFX + name + "_IMG", asTexture=True)
    cmds.setAttr(image_node + ".filename", texture_path, type="string")
    cmds.connectAttr(image_node + ".outColor", shader + ".baseColor", force=True)
    return shader

def assign_shader(obj, shader):
    """Assign a shader to one object."""
    cmds.select(obj)
    cmds.hyperShade(assign=shader)


def build_materials():
    """Create shaders line by line, then store them in the shaders dictionary."""
    shaders = {}

    shaders["chrome"] = make_shader("polished_chrome_SHD", (0.88, 0.90, 0.92), metalness=1.0, roughness=0.11)
    shaders["wire"] = make_shader("dark_wire_SHD", (0.08, 0.08, 0.08), metalness=1.0, roughness=0.22)
    shaders["floor"] = make_texture_shader("wood_floor_SHD", WOOD_TEXTURE_PATH, roughness=0.48)
    shaders["background"] = make_texture_shader("white_wall_SHD", WALL_TEXTURE_PATH, roughness=0.62)

    shaders["gold"] = make_shader("warm_gold_bell_SHD", (1.0, 0.58, 0.03), metalness=0.35, roughness=0.20)
    shaders["bright_gold"] = make_shader("bright_gold_bell_SHD", (1.0, 0.80, 0.08), metalness=0.25, roughness=0.18)
    shaders["orange"] = make_shader("orange_bell_detail_SHD", (0.88, 0.34, 0.02), metalness=0.15, roughness=0.25)

    shaders["red_wood"] = make_shader("painted_red_wood_SHD", (0.55, 0.08, 0.035), roughness=0.38)
    shaders["dark_red_wood"] = make_shader("dark_red_joinery_SHD", (0.34, 0.035, 0.02), roughness=0.42)

    shaders["stone"] = make_shader("warm_grey_stone_SHD", (0.47, 0.44, 0.39), roughness=0.58)
    shaders["stone_light"] = make_shader("light_grey_stone_SHD", (0.62, 0.59, 0.53), roughness=0.55)
    shaders["stone_dark"] = make_shader("dark_stone_groove_SHD", (0.22, 0.20, 0.18), roughness=0.65)

    return shaders


######################################
# 3. Modeling
######################################
#Create a beveled box for convenient reuse during subsequent modeling.
def make_box(name, pos, size, shader=None):
    obj = cmds.polyCube(w=size[0], h=size[1], d=size[2], n=PFX + name)[0]
    cmds.move(pos[0], pos[1], pos[2], obj)

    bevel_offset = min(0.035, max(0.002, min(size) * 0.16))
    cmds.polyBevel(obj + ".e[*]", offset=bevel_offset, segments=2)
    cmds.select(obj)
    cmds.DeleteHistory()

    if shader:
        assign_shader(obj, shader)

    return obj


def cylinder_between_points(name, start, end, radius, shader=None, sides=16):
    """Create a cylinder between two points, mainly used for pendulum wires."""
    sx, sy, sz = start
    ex, ey, ez = end

    dx = ex - sx
    dy = ey - sy
    dz = ez - sz
    length = math.sqrt(dx * dx + dy * dy + dz * dz)

    obj = cmds.polyCylinder(r=radius, h=length, sx=sides, n=PFX + name)[0]
    cmds.move((sx + ex) / 2.0, (sy + ey) / 2.0, (sz + ez) / 2.0, obj)

    rot_z = math.degrees(math.atan2(-dx, -dy))
    flat_length = math.sqrt(dx * dx + dy * dy)
    rot_x = math.degrees(math.atan2(-dz, flat_length))
    cmds.rotate(rot_x, 0, rot_z, obj)

    if shader:
        assign_shader(obj, shader)

    return obj


def make_floor_and_base(shaders):
    """Create the floor, stone platform, steps, tile grooves, and background wall."""
    base_parts = []

    floor = cmds.polyPlane(w=46, h=34, n=PFX + "wood_floor")[0]
    assign_shader(floor, shaders["floor"])
    base_parts.append(floor)

    base_parts.append(make_box("square_stone_platform", (0, 0.18, 0), (6.7, 0.36, 3.7), shaders["stone"]))
    base_parts.append(make_box("raised_square_stone_slab", (0, 0.45, 0), (5.95, 0.22, 3.15), shaders["stone_light"]))
    base_parts.append(make_box("front_stone_step_lower", (0, 0.09, 2.11), (2.70, 0.18, 0.52), shaders["stone"]))
    base_parts.append(make_box("front_stone_step_upper", (0, 0.27, 2.06), (2.15, 0.18, 0.42), shaders["stone_light"]))

    for x in (-2.0, -1.0, 0.0, 1.0, 2.0):
        groove = make_box("stone_tile_groove_x#", (x, 0.565, 0), (0.018, 0.012, 3.0), shaders["stone_dark"])
        base_parts.append(groove)

    for z in (-1.0, 0.0, 1.0):
        groove = make_box("stone_tile_groove_z#", (0, 0.57, z), (5.7, 0.012, 0.018), shaders["stone_dark"])
        base_parts.append(groove)

    backdrop = cmds.polyPlane(w=46, h=26, sx=1, sy=1, n=PFX + "white_background_wall")[0]
    cmds.rotate(90, 0, 0, backdrop)
    cmds.move(0, 9.4, -9.0, backdrop)
    assign_shader(backdrop, shaders["background"])
    base_parts.append(backdrop)

    return cmds.group(base_parts, n=PFX + "base_GRP")


def make_bell(index, x_pos, y_pos, shaders):
    """Create bell-shaped pendulum weight."""
    parts = []
    body_height = 0.50
    top_radius = 0.14
    bottom_radius = BELL_RADIUS
    bottom_y = y_pos - body_height * 0.5
    top_y = y_pos + body_height * 0.5

    body = cmds.polyCylinder(r=1, h=body_height, sx=48, sy=8, n=PFX + "pendulum_%02d_gold_bell_body" % index)[0]

    for vert in cmds.ls(body + ".vtx[*]", fl=True):
        px, py, pz = cmds.xform(vert, q=True, ws=True, t=True)
        height_percent = (py + body_height * 0.5) / body_height
        profile = top_radius + (bottom_radius - top_radius) * ((1.0 - height_percent) ** 0.75)
        cmds.xform(vert, ws=True, t=(px * profile, py, pz * profile))

    cmds.move(x_pos, y_pos, 0, body)
    assign_shader(body, shaders["gold"])
    parts.append(body)

    rim = cmds.polyTorus(r=bottom_radius * 0.98, sr=0.035, sx=48, sy=10, n=PFX + "pendulum_%02d_bell_bottom_rim" % index)[0]
    cmds.move(x_pos, bottom_y + 0.01, 0, rim)
    assign_shader(rim, shaders["bright_gold"])
    parts.append(rim)

    band_1 = cmds.polyTorus(r=bottom_radius * 0.78, sr=0.010, sx=48, sy=6, n=PFX + "pendulum_%02d_bell_band_01" % index)[0]
    cmds.move(x_pos, y_pos + 0.02, 0, band_1)
    assign_shader(band_1, shaders["orange"])
    parts.append(band_1)

    band_2 = cmds.polyTorus(r=bottom_radius * 0.63, sr=0.010, sx=48, sy=6, n=PFX + "pendulum_%02d_bell_band_02" % index)[0]
    cmds.move(x_pos, y_pos + 0.15, 0, band_2)
    assign_shader(band_2, shaders["orange"])
    parts.append(band_2)

    neck = cmds.polyCylinder(r=0.045, h=0.10, sx=18, n=PFX + "pendulum_%02d_bell_top_neck" % index)[0]
    cmds.move(x_pos, top_y + 0.045, 0, neck)
    assign_shader(neck, shaders["bright_gold"])
    parts.append(neck)

    handle = cmds.polyTorus(r=0.105, sr=0.022, sx=32, sy=8, n=PFX + "pendulum_%02d_bell_top_handle" % index)[0]
    cmds.rotate(90, 0, 0, handle)
    cmds.move(x_pos, top_y + 0.16, 0, handle)
    assign_shader(handle, shaders["bright_gold"])
    parts.append(handle)

    clapper_stem = cmds.polyCylinder(r=0.012, h=0.18, sx=10, n=PFX + "pendulum_%02d_bell_clapper_stem" % index)[0]
    cmds.move(x_pos, bottom_y - 0.07, 0, clapper_stem)
    assign_shader(clapper_stem, shaders["orange"])
    parts.append(clapper_stem)

    clapper = cmds.polySphere(r=0.055, sx=24, sy=12, n=PFX + "pendulum_%02d_bell_clapper" % index)[0]
    cmds.move(x_pos, bottom_y - 0.17, 0, clapper)
    assign_shader(clapper, shaders["bright_gold"])
    parts.append(clapper)

    attach_point = (x_pos, top_y + 0.16, 0)
    return parts, attach_point


def make_dougong_bracket(x, z, shaders):
    """Create one Chinese-style bracket cluster."""
    parts = []

    if x > 0:
        sign_x = 1
    else:
        sign_x = -1

    if z > 0:
        sign_z = 1
    else:
        sign_z = -1

    inward_x = -sign_x
    inward_z = -sign_z
    center_y = TOP_Y + 0.62
    top_y = TOP_Y + 0.88

    parts.append(make_box("dougong_center_front_block#", (x, center_y, z + sign_z * 0.20), (0.48, 0.16, 0.12), shaders["dark_red_wood"]))
    parts.append(make_box("dougong_center_back_block#", (x, center_y, z - sign_z * 0.20), (0.48, 0.16, 0.12), shaders["dark_red_wood"]))
    parts.append(make_box("dougong_center_left_block#", (x + sign_x * 0.20, center_y, z), (0.12, 0.16, 0.48), shaders["dark_red_wood"]))
    parts.append(make_box("dougong_center_right_block#", (x - sign_x * 0.20, center_y, z), (0.12, 0.16, 0.48), shaders["dark_red_wood"]))
    parts.append(make_box("dougong_beam_cap_x#", (x + inward_x * 0.33, top_y, z), (0.52, 0.18, 0.28), shaders["red_wood"]))
    parts.append(make_box("dougong_beam_cap_z#", (x, top_y, z + inward_z * 0.33), (0.28, 0.18, 0.52), shaders["red_wood"]))

    return parts


def make_frame(shaders):
    """Create the Chinese-style timber frame."""
    frame_parts = []

    post_bottom = 0.52
    post_top = TOP_Y + 1.18
    post_size = 0.26
    beam_extend = 0.48
    beam_len_x = FRAME_HALF_WIDTH * 2.0 + beam_extend * 2.0
    upper_beam_y = TOP_Y + 1.02

    for x in (-FRAME_HALF_WIDTH, FRAME_HALF_WIDTH):
        for z in (FRONT_Z, BACK_Z):
            frame_parts.append(make_box("stone_post_foot#", (x, 0.68, z), (0.48, 0.30, 0.48), shaders["stone"]))
            frame_parts.append(make_box("red_square_post#", (x, (post_bottom + post_top) / 2.0, z), (post_size, post_top - post_bottom, post_size), shaders["red_wood"]))
            frame_parts.append(make_box("post_top_cap#", (x, post_top + 0.13, z), (0.48, 0.26, 0.48), shaders["dark_red_wood"]))
            frame_parts.append(make_box("post_middle_block#", (x, TOP_Y, z), (0.44, 0.24, 0.44), shaders["dark_red_wood"]))

    for z in (FRONT_Z, BACK_Z):
        frame_parts.append(make_box("lower_red_hanging_beam#", (0, TOP_Y, z), (beam_len_x, 0.18, 0.22), shaders["red_wood"]))
        frame_parts.append(make_box("upper_red_architrave#", (0, upper_beam_y, z), (beam_len_x + 0.30, 0.22, 0.26), shaders["red_wood"]))
        frame_parts.append(make_box("inner_red_beam#", (0, TOP_Y + 0.48, z), (beam_len_x - 0.75, 0.16, 0.18), shaders["dark_red_wood"]))

    for x in (-FRAME_HALF_WIDTH, FRAME_HALF_WIDTH):
        frame_parts.append(make_box("side_lower_red_beam#", (x, TOP_Y, 0), (0.22, 0.18, (FRONT_Z - BACK_Z) + 0.55), shaders["red_wood"]))
        frame_parts.append(make_box("side_upper_red_beam#", (x, upper_beam_y, 0), (0.24, 0.22, (FRONT_Z - BACK_Z) + 0.75), shaders["red_wood"]))

    for x in (-FRAME_HALF_WIDTH, FRAME_HALF_WIDTH):
        for z in (FRONT_Z, BACK_Z):
            bracket_parts = make_dougong_bracket(x, z, shaders)
            frame_parts.extend(bracket_parts)

    hanger_start_x = -BELL_SPACING * (BALL_COUNT - 1) / 2.0
    for z in (FRONT_Z, BACK_Z):
        for i in range(BALL_COUNT):
            x = hanger_start_x + BELL_SPACING * i
            frame_parts.append(make_box("wood_hanger_block#", (x, TOP_Y - 0.02, z), (0.18, 0.26, 0.30), shaders["dark_red_wood"]))

    return cmds.group(frame_parts, n=PFX + "chinese_timber_frame_GRP")


def make_one_pendulum(index, x_pos, shaders):
    """Create one pendulum group: two wires plus one bell."""
    front_anchor = (x_pos, TOP_Y, FRONT_Z)
    back_anchor = (x_pos, TOP_Y, BACK_Z)
    bell_y = 1.32

    parts = []
    bell_parts, bell_attach_point = make_bell(index, x_pos, bell_y, shaders)

    front_wire = cylinder_between_points("pendulum_%02d_front_wire" % index, front_anchor, bell_attach_point, 0.012, shaders["wire"], sides=8)
    back_wire = cylinder_between_points("pendulum_%02d_back_wire" % index, back_anchor, bell_attach_point, 0.012, shaders["wire"], sides=8)

    parts.append(front_wire)
    parts.append(back_wire)
    parts.extend(bell_parts)

    group = cmds.group(parts, n=PFX + "pendulum_%02d_GRP" % index)

    cmds.xform(group, pivots=(x_pos, TOP_Y, 0), ws=True)

    return group


def make_pendulums(shaders):
    """Create five pendulums."""
    pendulum_groups = []
    start_x = -BELL_SPACING * (BALL_COUNT - 1) / 2.0

    for i in range(BALL_COUNT):
        x_pos = start_x + BELL_SPACING * i
        pendulum_number = i + 1
        group = make_one_pendulum(pendulum_number, x_pos, shaders)
        pendulum_groups.append(group)

    add_looping_pendulum_expressions(pendulum_groups)
    return cmds.group(pendulum_groups, n=PFX + "all_pendulums_GRP")


######################################
# 4. Animation
######################################

def add_looping_pendulum_expressions(pendulum_groups):
    """Create looping pendulum motion with a Maya expression."""
    cycle_length = END_FRAME - START_FRAME + 1
    cycle_angle = "6.2831853 * ((frame - %d) / %.1f)" % (START_FRAME, float(cycle_length))

    expr_lines = []
    expr_lines.append("// Looping Newton's cradle motion from frame %d to %d." % (START_FRAME, END_FRAME))
    expr_lines.append("%s.rotateZ = clamp(-22, 0, -sin(%s) * 22);" % (pendulum_groups[0], cycle_angle))
    expr_lines.append("%s.rotateZ = sin(%s * 2) * 0.6;" % (pendulum_groups[1], cycle_angle))
    expr_lines.append("%s.rotateZ = sin(%s * 2) * 0.6;" % (pendulum_groups[2], cycle_angle))
    expr_lines.append("%s.rotateZ = sin(%s * 2) * 0.6;" % (pendulum_groups[3], cycle_angle))
    expr_lines.append("%s.rotateZ = clamp(0, 22, -sin(%s) * 22);" % (pendulum_groups[4], cycle_angle))

    expression_text = "\n".join(expr_lines)
    cmds.expression(n=PFX + "pendulum_loop_EXPR", s=expression_text)


######################################
# 5. Lighting Setup
######################################

def make_hdri_skydome():
    """Create the HDRI skydome light."""
    hdri_path = HDRI_PATH

    skydome_shape = cmds.shadingNode("aiSkyDomeLight", asLight=True, name=PFX + "hdri_skyDomeShape")
    cmds.setAttr(skydome_shape + ".intensity", 0.75)

    if os.path.exists(hdri_path):
        image_node = cmds.shadingNode("aiImage", asTexture=True, name=PFX + "hdri_image")
        cmds.setAttr(image_node + ".filename", hdri_path, type="string")
        cmds.connectAttr(image_node + ".outColor", skydome_shape + ".color", force=True)
    else:
        print("HDRI file not found:", hdri_path)

    return PFX + "hdri_skyDome"


def make_lights():
    """Create the key light, rim light, and skydome light."""
    key = cmds.shadingNode("aiAreaLight", asLight=True, name=PFX + "large_softbox_keyShape")
    cmds.move(-7.2, 8.6, 6.8, PFX + "large_softbox_key")
    cmds.rotate(-46, -40, 0, PFX + "large_softbox_key")
    cmds.scale(7.0, 4.2, 1.0, PFX + "large_softbox_key")
    cmds.setAttr(key + ".intensity", 850)
    cmds.setAttr(key + ".exposure", 1.35)

    rim = cmds.shadingNode("aiAreaLight", asLight=True, name=PFX + "thin_rim_lightShape")
    cmds.move(10.5, 8.0, -12.0, PFX + "thin_rim_light")
    cmds.rotate(-34, 140, 0, PFX + "thin_rim_light")
    cmds.scale(5.0, 3.0, 1.0, PFX + "thin_rim_light")
    cmds.setAttr(rim + ".intensity", 460)
    cmds.setAttr(rim + ".exposure", 1.1)

    skydome = make_hdri_skydome()
    lights_group = cmds.group(PFX + "large_softbox_key", PFX + "thin_rim_light", skydome, n=PFX + "lights_GRP")
    return lights_group


######################################
# 6. Camera Setup
######################################

def make_camera():
    """Create the render camera."""
    camera = cmds.camera(name=PFX + "render_camera")[0]
    cmds.move(2.2, 2.8, 11.1, camera)
    cmds.rotate(-0.6, 11.1, 0.3, camera)
    cmds.setAttr(camera + ".focalLength", 32)

    for camera_shape in cmds.ls(type="camera"):
        cmds.setAttr(camera_shape + ".renderable", 0)

    camera_shape = cmds.listRelatives(camera, shapes=True)[0]
    cmds.setAttr(camera_shape + ".renderable", 1)

    return camera


def set_timeline_and_render_settings():
    """Set the timeline, looping playback, resolution, and renderer."""
    cmds.playbackOptions(min=START_FRAME, max=END_FRAME, ast=START_FRAME, aet=END_FRAME, loop="continuous")
    cmds.setAttr("defaultResolution.width", FULL_WIDTH)
    cmds.setAttr("defaultResolution.height", FULL_HEIGHT)
    cmds.setAttr("defaultResolution.deviceAspectRatio", float(FULL_WIDTH) / FULL_HEIGHT)

    if cmds.objExists("defaultRenderGlobals"):
        cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")


######################################
######################################

def main():
    """Build the complete scene in order."""
    clear_previous_build()

    shaders = build_materials()

    base_group = make_floor_and_base(shaders)
    frame_group = make_frame(shaders)
    pendulum_group = make_pendulums(shaders)

    lights_group = make_lights()
    camera = make_camera()
    set_timeline_and_render_settings()

    master_group = cmds.group(base_group, frame_group, pendulum_group, lights_group, camera, n=PFX + "MASTER_GRP")
    cmds.select(master_group)


main()
