#################################################
# SP26_VFX705_01_Siyuan_Pang_P04_TreeScatter_FINAL_v01.py
# By: Siyuan Pang
# Created: 26-May-2026
#################################################

###########################################################################################
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
                return ["mock_result"]
            return mock

    cmds = MockCmds()
##########################################################################################
##########################################################################################
##########################################################################################

import math
import os
import sys
from random import uniform, randint, choice

import maya.cmds as cmds
import maya.api.OpenMaya as om


##########################################################################################
# BASIC SETTINGS
##########################################################################################

PFX = "ZL_TC_"
FOREST_GRP = PFX + "Forest_GRP"
HDRI_PATH = r"C:\Users\Administrator\Desktop\Third Semester\705\04\qwantani_noon_puresky_4k.exr"


##########################################################################################
# CLEANUP AND SELECTION
##########################################################################################

def clean_up():
    # Delete only old objects, materials, and groups made by this script.
    old_nodes = cmds.ls(PFX + "*", long=True) or []

    if old_nodes:
        cmds.delete(old_nodes)


def get_points():
    # Read the selected vertices in flattened form.
    points_selected = cmds.ls(sl=1, fl=1) or []
    selected_vertices = []

    for item in points_selected:
        if ".vtx[" in item:
            selected_vertices.append(item)

    if len(selected_vertices) == 0:
        sys.exit(0)

    return selected_vertices


def find_xyz_pos(vertex):
    # Convert one selected vertex into a world position.
    curr_xyz = cmds.pointPosition(vertex, world=True)
    return curr_xyz


##########################################################################################
# SHADERS
##########################################################################################

def mk_shader(shader_name, color, roughness=0.75, metalness=0.0):
    # Create one Arnold aiStandardSurface shader.
    shader = cmds.shadingNode("aiStandardSurface", asShader=True, name=shader_name)
    cmds.setAttr(shader + ".baseColor", color[0], color[1], color[2], type="double3")
    cmds.setAttr(shader + ".specularRoughness", roughness)
    cmds.setAttr(shader + ".metalness", metalness)
    return shader


def assign_shader(obj, shader):
    # Assign one shader to one object.
    cmds.select(obj, replace=True)
    cmds.hyperShade(assign=shader)


def darker_color(color, amount=0.55):
    # Make a deeper version of the same color.
    return (
        max(0.0, color[0] * amount),
        max(0.0, color[1] * amount),
        max(0.0, color[2] * amount),
    )


def set_attr_if_exists(node, attr_name, value):
    # Some Maya texture nodes have different attributes between versions.
    if cmds.attributeQuery(attr_name, node=node, exists=True):
        full_attr = node + "." + attr_name

        try:
            attr_type = cmds.getAttr(full_attr, type=True)
        except RuntimeError:
            attr_type = None

        try:
            if attr_type == "double3":
                cmds.setAttr(full_attr, value, value, value, type="double3")
            elif attr_type == "float3":
                cmds.setAttr(full_attr, value, value, value, type="float3")
            else:
                cmds.setAttr(full_attr, value)
        except RuntimeError:
            pass


def get_scalar_output_attr(node):
    # Return a usable single-channel output from different texture node types.
    if not cmds.objExists(node):
        return None

    if cmds.attributeQuery("outColorR", node=node, exists=True):
        return node + ".outColorR"

    if cmds.attributeQuery("outAlpha", node=node, exists=True):
        return node + ".outAlpha"

    return None


def mk_cell_texture(node_name, density):
    # Try Arnold aiCellNoise first because it gives rounder spots than regular noise.
    texture = None

    for node_type in ["aiCellNoise", "noise"]:
        try:
            texture = cmds.shadingNode(node_type, asTexture=True, name=node_name)
        except RuntimeError:
            texture = None

        if texture and get_scalar_output_attr(texture):
            break

    if not texture or not get_scalar_output_attr(texture):
        texture = cmds.shadingNode("noise", asTexture=True, name=node_name + "_noiseFallback")

    set_attr_if_exists(texture, "scale", density)
    set_attr_if_exists(texture, "density", density)
    set_attr_if_exists(texture, "frequency", density)
    set_attr_if_exists(texture, "randomness", 0.72)
    set_attr_if_exists(texture, "jitter", 0.58)
    set_attr_if_exists(texture, "octaves", 3)
    set_attr_if_exists(texture, "lacunarity", 2.4)
    return texture


def connect_bump_from_mask(shader, mask_node, bump_name, depth):
    # Bump changes the render normal. It looks raised, but it does not add real geometry.
    mask_output = get_scalar_output_attr(mask_node)

    if not mask_output:
        return None

    bump = cmds.shadingNode("bump2d", asUtility=True, name=bump_name)
    cmds.setAttr(bump + ".bumpDepth", depth)
    cmds.connectAttr(mask_output, bump + ".bumpValue", force=True)

    if cmds.attributeQuery("normalCamera", node=shader, exists=True):
        cmds.connectAttr(bump + ".outNormal", shader + ".normalCamera", force=True)

    return bump


def mk_bark_cell_shader(shader_name, color, roughness=0.75, metalness=0.0):
    # Add clear cellular spots and bump to the trunk and branches.
    shader = mk_shader(shader_name, color, roughness, metalness)
    dark = darker_color(color, 0.42)
    light = (
        min(1.0, color[0] * 1.22),
        min(1.0, color[1] * 1.22),
        min(1.0, color[2] * 1.22),
    )
    cell = mk_cell_texture(shader_name + "_cell_TEX", 4)
    ramp = cmds.shadingNode("ramp", asTexture=True, name=shader_name + "_cellRamp_TEX")
    cell_output = get_scalar_output_attr(cell)

    cmds.setAttr(ramp + ".colorEntryList[0].position", 0.38)
    cmds.setAttr(ramp + ".colorEntryList[0].color", dark[0], dark[1], dark[2], type="double3")
    cmds.setAttr(ramp + ".colorEntryList[1].position", 0.44)
    cmds.setAttr(ramp + ".colorEntryList[1].color", color[0], color[1], color[2], type="double3")
    cmds.setAttr(ramp + ".colorEntryList[2].position", 0.82)
    cmds.setAttr(ramp + ".colorEntryList[2].color", light[0], light[1], light[2], type="double3")

    if cmds.attributeQuery("interpolation", node=ramp, exists=True):
        cmds.setAttr(ramp + ".interpolation", 0)

    if cell_output:
        cmds.connectAttr(cell_output, ramp + ".vCoord", force=True)

    cmds.connectAttr(ramp + ".outColor", shader + ".baseColor", force=True)
    connect_bump_from_mask(shader, cell, shader_name + "_cellBump_BMP", 0.075)
    return shader


def mk_canopy_cell_shader(shader_name, color):
    # Use cellular and ramp to create darker round spots inside one color family.
    shader = mk_shader(shader_name, color, 0.58, 0.0)
    dark = darker_color(color, 0.44)
    cell = mk_cell_texture(shader_name + "_aiCellNoise_TEX", 6)
    ramp = cmds.shadingNode("ramp", asTexture=True, name=shader_name + "_spotRamp_TEX")
    cell_output = get_scalar_output_attr(cell)

    cmds.setAttr(ramp + ".colorEntryList[0].position", 0.40)
    cmds.setAttr(ramp + ".colorEntryList[0].color", dark[0], dark[1], dark[2], type="double3")
    cmds.setAttr(ramp + ".colorEntryList[1].position", 0.46)
    cmds.setAttr(ramp + ".colorEntryList[1].color", color[0], color[1], color[2], type="double3")

    if cmds.attributeQuery("interpolation", node=ramp, exists=True):
        cmds.setAttr(ramp + ".interpolation", 0)

    if cell_output:
        cmds.connectAttr(cell_output, ramp + ".vCoord", force=True)

    cmds.connectAttr(ramp + ".outColor", shader + ".baseColor", force=True)
    connect_bump_from_mask(shader, cell, shader_name + "_cellBump_BMP", 0.055)
    return shader


def mk_leaf_stripe_shader(shader_name, color):
    # Use a repeated ramp to make darker radial stripe bands on the bowl leaves.
    shader = mk_shader(shader_name, color, 0.58, 0.0)
    dark = darker_color(color, 0.50)
    place = cmds.shadingNode("place2dTexture", asUtility=True, name=shader_name + "_place2d_TEX")
    ramp = cmds.shadingNode("ramp", asTexture=True, name=shader_name + "_stripeRamp_TEX")

    cmds.setAttr(place + ".repeatU", 12)
    cmds.setAttr(place + ".repeatV", 1)

    if cmds.attributeQuery("type", node=ramp, exists=True):
        cmds.setAttr(ramp + ".type", 1)

    if cmds.attributeQuery("interpolation", node=ramp, exists=True):
        cmds.setAttr(ramp + ".interpolation", 0)

    cmds.setAttr(ramp + ".colorEntryList[0].position", 0.00)
    cmds.setAttr(ramp + ".colorEntryList[0].color", dark[0], dark[1], dark[2], type="double3")
    cmds.setAttr(ramp + ".colorEntryList[1].position", 0.10)
    cmds.setAttr(ramp + ".colorEntryList[1].color", dark[0], dark[1], dark[2], type="double3")
    cmds.setAttr(ramp + ".colorEntryList[2].position", 0.16)
    cmds.setAttr(ramp + ".colorEntryList[2].color", color[0], color[1], color[2], type="double3")
    cmds.setAttr(ramp + ".colorEntryList[3].position", 1.00)
    cmds.setAttr(ramp + ".colorEntryList[3].color", color[0], color[1], color[2], type="double3")

    cmds.connectAttr(place + ".outUV", ramp + ".uvCoord", force=True)
    cmds.connectAttr(place + ".outUvFilterSize", ramp + ".uvFilterSize", force=True)
    cmds.connectAttr(ramp + ".outColor", shader + ".baseColor", force=True)
    return shader


def mk_all_shaders():
    # Keep the palette away from normal green and brown tree colors.
    rose_quartz = (0.92, 0.38, 0.62)
    glacier_cyan = (0.28, 0.74, 0.86)
    amber_glass = (0.96, 0.62, 0.24)

    shaders = {
        "bark_a": mk_bark_cell_shader(PFX + "violetGraphite_SHD", (0.23, 0.20, 0.33), 0.82, 0.02),
        "bark_b": mk_bark_cell_shader(PFX + "frostCopper_SHD", (0.72, 0.44, 0.28), 0.70, 0.08),
        "bark_c": mk_bark_cell_shader(PFX + "blueAsh_SHD", (0.32, 0.42, 0.58), 0.85, 0.00),
        "leaf_a": mk_leaf_stripe_shader(PFX + "roseQuartzLeaf_SHD", rose_quartz),
        "leaf_b": mk_leaf_stripe_shader(PFX + "glacierCyanLeaf_SHD", glacier_cyan),
        "leaf_c": mk_leaf_stripe_shader(PFX + "amberGlassLeaf_SHD", amber_glass),
        "canopy_a": mk_canopy_cell_shader(PFX + "roseQuartzCanopy_SHD", rose_quartz),
        "canopy_b": mk_canopy_cell_shader(PFX + "glacierCyanCanopy_SHD", glacier_cyan),
        "canopy_c": mk_canopy_cell_shader(PFX + "amberGlassCanopy_SHD", amber_glass),
    }

    return shaders


##########################################################################################
# SMALL MATH HELPERS
##########################################################################################

def lerp_point(point_a, point_b, amount):
    # Linearly blend between two XYZ points.
    x_pos = point_a[0] + (point_b[0] - point_a[0]) * amount
    y_pos = point_a[1] + (point_b[1] - point_a[1]) * amount
    z_pos = point_a[2] + (point_b[2] - point_a[2]) * amount
    return (x_pos, y_pos, z_pos)


def sample_curve_points(points, amount):
    # Read an approximate point along a list of curve points.
    if amount <= 0:
        return points[0]

    if amount >= 1:
        return points[-1]

    scaled_amount = amount * (len(points) - 1)
    point_index = int(math.floor(scaled_amount))
    local_amount = scaled_amount - point_index
    return lerp_point(points[point_index], points[point_index + 1], local_amount)


def vec_sub(point_a, point_b):
    return (point_a[0] - point_b[0], point_a[1] - point_b[1], point_a[2] - point_b[2])


def vec_length(vec):
    return math.sqrt(vec[0] * vec[0] + vec[1] * vec[1] + vec[2] * vec[2])


def vec_normalize(vec):
    length = vec_length(vec)

    if length < 0.0001:
        return (0.0, 1.0, 0.0)

    return (vec[0] / length, vec[1] / length, vec[2] / length)


def vec_cross(vec_a, vec_b):
    return (
        vec_a[1] * vec_b[2] - vec_a[2] * vec_b[1],
        vec_a[2] * vec_b[0] - vec_a[0] * vec_b[2],
        vec_a[0] * vec_b[1] - vec_a[1] * vec_b[0],
    )


def vec_scale(vec, amount):
    return (vec[0] * amount, vec[1] * amount, vec[2] * amount)


def vec_add(vec_a, vec_b):
    return (vec_a[0] + vec_b[0], vec_a[1] + vec_b[1], vec_a[2] + vec_b[2])


def offset_point(point, direction_a, amount_a, direction_b, amount_b):
    # Move a point by two direction vectors. This keeps top branches aligned to the trunk frame.
    return (
        point[0] + direction_a[0] * amount_a + direction_b[0] * amount_b,
        point[1] + direction_a[1] * amount_a + direction_b[1] * amount_b,
        point[2] + direction_a[2] * amount_a + direction_b[2] * amount_b,
    )


def rotate_point_xyz(point, rotation):
    # Rotate one local point by XYZ degrees.
    rx = math.radians(rotation[0])
    ry = math.radians(rotation[1])
    rz = math.radians(rotation[2])

    x_pos = point.x
    y_pos = point.y
    z_pos = point.z

    # Rotate around X.
    y_after_x = y_pos * math.cos(rx) - z_pos * math.sin(rx)
    z_after_x = y_pos * math.sin(rx) + z_pos * math.cos(rx)
    x_after_x = x_pos

    # Rotate around Y.
    x_after_y = x_after_x * math.cos(ry) + z_after_x * math.sin(ry)
    z_after_y = -x_after_x * math.sin(ry) + z_after_x * math.cos(ry)
    y_after_y = y_after_x

    # Rotate around Z.
    x_after_z = x_after_y * math.cos(rz) - y_after_y * math.sin(rz)
    y_after_z = x_after_y * math.sin(rz) + y_after_y * math.cos(rz)
    z_after_z = z_after_y

    return (x_after_z, y_after_z, z_after_z)


def local_point_to_world(local_point, object_pos, object_rotation):
    # Convert a point from leaf local space into world space.
    rotated_point = rotate_point_xyz(local_point, object_rotation)
    world_point = (
        object_pos[0] + rotated_point[0],
        object_pos[1] + rotated_point[1],
        object_pos[2] + rotated_point[2],
    )
    return world_point


def get_curve_tangent(curve_points, amount):
    # Use two nearby sampled points to estimate a curve direction.
    delta = 0.015
    prev_pos = sample_curve_points(curve_points, max(0.0, amount - delta))
    next_pos = sample_curve_points(curve_points, min(1.0, amount + delta))
    tangent = vec_sub(next_pos, prev_pos)
    return vec_normalize(tangent)


def get_curve_frame(curve_points, amount):
    # Build two side vectors around the curve direction.
    tangent = get_curve_tangent(curve_points, amount)
    normal = vec_cross((0.0, 1.0, 0.0), tangent)

    if vec_length(normal) < 0.0001:
        normal = (1.0, 0.0, 0.0)
    else:
        normal = vec_normalize(normal)

    binormal = vec_cross(tangent, normal)
    binormal = vec_normalize(binormal)
    return normal, binormal


##########################################################################################
# TRUNK
##########################################################################################

def mk_guide_curve(cnt, base_pos):
    # Create a twisted guide curve rising from one selected vertex.
    x_pos, y_pos, z_pos = base_pos
    curve_points = []

    height = uniform(3.8, 5.8)
    turns = uniform(0.85, 1.55)
    spiral_radius = uniform(0.48, 0.95)
    start_angle = uniform(0.0, math.tau)
    drift_x = uniform(-0.25, 0.25)
    drift_z = uniform(-0.25, 0.25)
    root_sink = uniform(0.28, 0.55)
    point_count = 30

    for i in range(point_count):
        amount = i / float(point_count - 1)

        if amount < 0.10:
            root_amount = amount / 0.10
            px = x_pos
            py = y_pos - root_sink * (1.0 - root_amount)
            pz = z_pos
            curve_points.append((px, py, pz))
        else:
            grow_amount = (amount - 0.10) / 0.90
            angle = start_angle + grow_amount * turns * math.tau
            radius_scale = min(1.0, grow_amount / 0.22)
            radius = spiral_radius * radius_scale * (1.0 - 0.16 * grow_amount)
            wobble = uniform(-0.08, 0.08)

            px = x_pos + math.cos(angle) * (radius + wobble * radius_scale) + drift_x * grow_amount
            py = y_pos + height * grow_amount
            pz = z_pos + math.sin(angle) * (radius + wobble * radius_scale) + drift_z * grow_amount
            curve_points.append((px, py, pz))

    guide_curve = cmds.curve(
        degree=3,
        point=curve_points,
        name=f"{PFX}Tree_{int(cnt):03d}_guide_CRV",
    )

    return guide_curve, curve_points


def taper_trunk_bottom(trunk, curve_points):
    # Smoothly shrink the lowest trunk vertices toward the guide curve center.
    taper_end = 0.24
    min_scale = 0.32
    sample_count = 28
    center_samples = []

    for i in range(sample_count):
        amount = taper_end * i / float(sample_count - 1)
        center_samples.append((amount, sample_curve_points(curve_points, amount)))

    trunk_vertices = cmds.ls(trunk + ".vtx[*]", fl=1) or []

    for vert in trunk_vertices:
        vert_pos = cmds.pointPosition(vert, world=True)
        closest_amount = None
        closest_center = None
        closest_dist = None

        for amount, center_pos in center_samples:
            dist_x = vert_pos[0] - center_pos[0]
            dist_y = vert_pos[1] - center_pos[1]
            dist_z = vert_pos[2] - center_pos[2]
            dist = dist_x * dist_x + dist_y * dist_y + dist_z * dist_z

            if closest_dist is None or dist < closest_dist:
                closest_amount = amount
                closest_center = center_pos
                closest_dist = dist

        if closest_amount is not None:
            amount_normalized = closest_amount / taper_end
            smooth_amount = amount_normalized * amount_normalized * amount_normalized
            smooth_amount = smooth_amount * (amount_normalized * (amount_normalized * 6.0 - 15.0) + 10.0)
            scale_amount = min_scale + (1.0 - min_scale) * smooth_amount

            new_x = closest_center[0] + (vert_pos[0] - closest_center[0]) * scale_amount
            new_y = closest_center[1] + (vert_pos[1] - closest_center[1]) * scale_amount
            new_z = closest_center[2] + (vert_pos[2] - closest_center[2]) * scale_amount

            cmds.move(new_x, new_y, new_z, vert, worldSpace=True)


def mk_trunk(cnt, tree_grp, base_pos, bark_shader):
    # Build the trunk with a circle profile extruded along a guide curve.
    guide_curve, curve_points = mk_guide_curve(cnt, base_pos)
    base_radius = uniform(0.30, 0.52)
    top_scale = uniform(0.22, 0.36)
    side_count = randint(20, 32)

    profile_curve = cmds.circle(
        name=f"{PFX}Tree_{int(cnt):03d}_trunkProfile_CRV",
        center=(0, 0, 0),
        normal=(0, 1, 0),
        radius=base_radius,
        sections=side_count,
        constructionHistory=False,
    )[0]
    cmds.move(curve_points[0][0], curve_points[0][1], curve_points[0][2], profile_curve)

    surface_result = cmds.extrude(
        profile_curve,
        guide_curve,
        n=f"{PFX}Tree_{int(cnt):03d}_trunk_SURF",
        ch=False,
        rn=False,
        po=0,
        et=2,
        ucp=True,
        fpt=True,
        upn=True,
        ro=0,
        sc=top_scale,
    )
    trunk_surface = surface_result[0]

    poly_result = cmds.nurbsToPoly(
        trunk_surface,
        n=f"{PFX}Tree_{int(cnt):03d}_trunk_GEO",
        ch=False,
        f=2,
        pt=1,
        ut=1,
        un=side_count,
        vt=1,
        vn=randint(32, 48),
    )
    trunk = poly_result[0]
    trunk = cmds.rename(trunk, f"{PFX}Tree_{int(cnt):03d}_trunk_GEO")

    taper_trunk_bottom(trunk, curve_points)
    assign_shader(trunk, bark_shader)

    cmds.delete(profile_curve)
    cmds.delete(trunk_surface)
    cmds.parent(guide_curve, tree_grp)
    cmds.parent(trunk, tree_grp)

    cmds.select(trunk, replace=True)
    cmds.polySoftEdge(angle=85)
    cmds.DeleteHistory()

    top_radius = base_radius * top_scale
    return trunk, guide_curve, curve_points, top_radius, side_count


def mk_trunk_top_cap(cnt, curve_points, top_radius, side_count, tree_grp, bark_shader):
    # Close the open top of the trunk.
    top_center = curve_points[-1]
    normal, binormal = get_curve_frame(curve_points, 1.0)

    vertices = [om.MPoint(top_center[0], top_center[1], top_center[2])]

    for i in range(side_count):
        angle = math.tau * i / float(side_count)
        side_offset = vec_add(
            vec_scale(normal, math.cos(angle) * top_radius),
            vec_scale(binormal, math.sin(angle) * top_radius),
        )
        vertices.append(om.MPoint(
            top_center[0] + side_offset[0],
            top_center[1] + side_offset[1],
            top_center[2] + side_offset[2],
        ))

    face_counts = []
    face_connects = []

    for i in range(side_count):
        next_i = 1 if i == side_count - 1 else i + 2
        face_counts.append(3)
        face_connects.extend([0, i + 1, next_i])

    mesh_fn = om.MFnMesh()
    mesh_obj = mesh_fn.create(vertices, face_counts, face_connects)
    cap = om.MFnDagNode(mesh_obj).fullPathName()
    cap = cmds.rename(cap, f"{PFX}Tree_{int(cnt):03d}_trunkTopCap_GEO")

    assign_shader(cap, bark_shader)
    cmds.parent(cap, tree_grp)
    cmds.select(cap, replace=True)
    cmds.polySoftEdge(angle=85)
    cmds.DeleteHistory()

    return cap


##########################################################################################
# BRANCHES, LEAVES, AND DROPS
##########################################################################################

def mk_leaf_branch(cnt, leaf_num, trunk_pos, tree_grp, branch_shader, branch_angle=None):
    # Create a curved branch. The last point pushes upward into the bowl leaf.
    if branch_angle is None:
        angle = uniform(0.0, math.tau)
    else:
        angle = branch_angle

    length = uniform(2.05, 2.85)
    height_offset = uniform(0.35, 0.78)
    side_twist = uniform(0.28, 0.58)

    dir_x = math.cos(angle)
    dir_z = math.sin(angle)
    side_x = -dir_z
    side_z = dir_x

    leaf_anchor = (
        trunk_pos[0] + dir_x * length,
        trunk_pos[1] + height_offset,
        trunk_pos[2] + dir_z * length,
    )
    hidden_end = (
        leaf_anchor[0],
        leaf_anchor[1] + uniform(0.12, 0.22),
        leaf_anchor[2],
    )

    branch_points = [
        trunk_pos,
        (
            trunk_pos[0] + dir_x * length * 0.20 + side_x * side_twist,
            trunk_pos[1] + height_offset * 0.20 + uniform(-0.10, 0.12),
            trunk_pos[2] + dir_z * length * 0.20 + side_z * side_twist,
        ),
        (
            trunk_pos[0] + dir_x * length * 0.46 - side_x * side_twist * 0.95,
            trunk_pos[1] + height_offset * 0.44 + uniform(-0.16, 0.14),
            trunk_pos[2] + dir_z * length * 0.46 - side_z * side_twist * 0.95,
        ),
        (
            trunk_pos[0] + dir_x * length * 0.76 + side_x * side_twist * 0.55,
            trunk_pos[1] + height_offset * 0.78 + uniform(-0.10, 0.12),
            trunk_pos[2] + dir_z * length * 0.76 + side_z * side_twist * 0.55,
        ),
        hidden_end,
    ]

    branch_curve = cmds.curve(
        degree=3,
        point=branch_points,
        name=f"{PFX}Tree_{int(cnt):03d}_branch_{int(leaf_num):02d}_CRV",
    )

    profile_curve = cmds.circle(
        name=f"{PFX}Tree_{int(cnt):03d}_branchProfile_{int(leaf_num):02d}_CRV",
        center=(0, 0, 0),
        normal=(0, 1, 0),
        radius=uniform(0.14, 0.22),
        sections=14,
        constructionHistory=False,
    )[0]
    cmds.move(trunk_pos[0], trunk_pos[1], trunk_pos[2], profile_curve)

    surface_result = cmds.extrude(
        profile_curve,
        branch_curve,
        n=f"{PFX}Tree_{int(cnt):03d}_branch_{int(leaf_num):02d}_SURF",
        ch=False,
        rn=False,
        po=0,
        et=2,
        ucp=True,
        fpt=True,
        upn=True,
        ro=0,
        sc=uniform(0.22, 0.36),
    )
    branch_surface = surface_result[0]

    poly_result = cmds.nurbsToPoly(
        branch_surface,
        n=f"{PFX}Tree_{int(cnt):03d}_branch_{int(leaf_num):02d}_GEO",
        ch=False,
        f=2,
        pt=1,
        ut=1,
        un=14,
        vt=1,
        vn=12,
    )
    branch_geo = poly_result[0]
    branch_geo = cmds.rename(branch_geo, f"{PFX}Tree_{int(cnt):03d}_branch_{int(leaf_num):02d}_GEO")

    assign_shader(branch_geo, branch_shader)

    cmds.delete(profile_curve)
    cmds.delete(branch_surface)
    cmds.parent(branch_curve, branch_geo, tree_grp)

    cmds.select(branch_geo, replace=True)
    cmds.polySoftEdge(angle=80)
    cmds.DeleteHistory()

    y_rotation = math.degrees(math.atan2(dir_x, dir_z))
    return leaf_anchor, y_rotation


def mk_bowl_leaf(cnt, leaf_num, leaf_anchor, y_rotation, tree_grp, leaf_shader):
    # Create a full circular bowl leaf with thickness.
    radial_steps = 7
    arc_steps = 24

    width = uniform(0.95, 1.55)
    depth = uniform(0.70, 1.15)
    cup_height = depth * uniform(0.35, 0.45)
    rim_lift = uniform(0.09, 0.17)
    thickness = uniform(0.045, 0.085)

    top_vertices = []
    top_faces = []
    grid_indices = []

    for r_index in range(radial_steps + 1):
        row = []
        radius_amount = r_index / float(radial_steps)

        for a_index in range(arc_steps):
            angle = math.tau * (a_index / float(arc_steps))
            pair_index = a_index // 2
            lobe_mask = 1.0 if pair_index % 2 == 0 else 0.0
            lobe_scale = 1.0 + 0.18 * lobe_mask * (radius_amount ** 1.35)

            x_pos = math.sin(angle) * radius_amount * width * lobe_scale
            z_pos = math.cos(angle) * radius_amount * depth * lobe_scale
            rim_amount = max(0.0, (radius_amount - 0.78) / 0.22)
            y_pos = cup_height * (radius_amount * radius_amount) + rim_lift * (rim_amount ** 1.4)

            row.append(len(top_vertices))
            top_vertices.append(om.MPoint(x_pos, y_pos, z_pos))

        grid_indices.append(row)

    for r_index in range(radial_steps):
        for a_index in range(arc_steps):
            next_a = (a_index + 1) % arc_steps
            top_faces.append([
                grid_indices[r_index][a_index],
                grid_indices[r_index + 1][a_index],
                grid_indices[r_index + 1][next_a],
                grid_indices[r_index][next_a],
            ])

    vertices = []
    face_counts = []
    face_connects = []

    for point in top_vertices:
        vertices.append(om.MPoint(point.x, point.y + thickness, point.z))

    for point in top_vertices:
        vertices.append(om.MPoint(point.x, point.y, point.z))

    layer_size = len(top_vertices)
    u_values = []
    v_values = []

    for layer_num in range(2):
        for r_index in range(radial_steps + 1):
            for a_index in range(arc_steps):
                u_values.append(a_index / float(arc_steps))
                v_values.append(r_index / float(radial_steps))

    for face in top_faces:
        face_counts.append(4)
        face_connects.extend(face)

    for face in top_faces:
        face_counts.append(4)
        face_connects.extend([index + layer_size for index in reversed(face)])

    outer_ring = grid_indices[radial_steps] + [grid_indices[radial_steps][0]]

    for i in range(len(outer_ring) - 1):
        a = outer_ring[i]
        b = outer_ring[i + 1]
        face_counts.append(4)
        face_connects.extend([a, b, b + layer_size, a + layer_size])

    mesh_fn = om.MFnMesh()
    mesh_obj = mesh_fn.create(vertices, face_counts, face_connects)

    try:
        mesh_fn.setUVs(u_values, v_values)
        mesh_fn.assignUVs(face_counts, face_connects)
    except RuntimeError:
        pass

    leaf = om.MFnDagNode(mesh_obj).fullPathName()
    leaf = cmds.rename(leaf, f"{PFX}Tree_{int(cnt):03d}_leaf_{int(leaf_num):02d}_GEO")

    leaf_rotation = (
        uniform(-2, 5),
        y_rotation + uniform(-4, 4),
        uniform(-5, 5),
    )
    cmds.move(leaf_anchor[0], leaf_anchor[1], leaf_anchor[2], leaf)
    cmds.rotate(leaf_rotation[0], leaf_rotation[1], leaf_rotation[2], leaf)

    assign_shader(leaf, leaf_shader)
    cmds.parent(leaf, tree_grp)
    cmds.select(leaf, replace=True)
    cmds.polySoftEdge(angle=70)
    cmds.DeleteHistory()

    drop_count = randint(0, 2)

    for drop_num in range(1, drop_count + 1):
        r_index = randint(3, radial_steps)
        a_index = randint(0, arc_steps - 1)
        attach_point = top_vertices[grid_indices[r_index][a_index]]
        drop_pos = om.MPoint(attach_point.x, attach_point.y, attach_point.z)
        drop_world_pos = local_point_to_world(drop_pos, leaf_anchor, leaf_rotation)
        mk_leaf_drop(cnt, leaf_num, drop_num, drop_world_pos, tree_grp, leaf_shader)

    return leaf


def mk_leaf_drop(cnt, leaf_num, drop_num, world_pos, tree_grp, leaf_shader):
    # Create one long closed liquid drop straight down in world Y.
    drop_length = uniform(0.82, 1.22)
    side_count = 18
    drop_rings = [
        (0.00, 0.014),
        (0.15, 0.022),
        (0.34, 0.030),
        (0.54, 0.042),
        (0.72, 0.066),
        (0.88, 0.108),
        (0.97, 0.082),
    ]

    twist = uniform(0.0, math.tau)
    sway_angle = uniform(0.0, math.tau)
    sway_amount = uniform(0.015, 0.045)

    vertices = []

    for height_amount, ring_radius in drop_rings:
        center_x = world_pos[0] + math.cos(sway_angle) * math.sin(height_amount * math.pi) * sway_amount
        center_z = world_pos[2] + math.sin(sway_angle) * math.sin(height_amount * math.pi) * sway_amount

        for i in range(side_count):
            angle = twist + math.tau * i / float(side_count)
            small_wobble = 1.0 + uniform(-0.012, 0.012)
            x_pos = center_x + math.cos(angle) * ring_radius * small_wobble
            y_pos = world_pos[1] - drop_length * height_amount
            z_pos = center_z + math.sin(angle) * ring_radius * small_wobble
            vertices.append(om.MPoint(x_pos, y_pos, z_pos))

    face_counts = []
    face_connects = []

    for ring_index in range(len(drop_rings) - 1):
        start = ring_index * side_count
        next_start = (ring_index + 1) * side_count

        for i in range(side_count):
            next_i = (i + 1) % side_count
            face_counts.append(4)
            face_connects.extend([
                start + i,
                start + next_i,
                next_start + next_i,
                next_start + i,
            ])

    top_center = len(vertices)
    vertices.append(om.MPoint(world_pos[0], world_pos[1], world_pos[2]))

    bottom_center = len(vertices)
    vertices.append(om.MPoint(
        world_pos[0] + math.cos(sway_angle) * sway_amount * 0.2,
        world_pos[1] - drop_length,
        world_pos[2] + math.sin(sway_angle) * sway_amount * 0.2,
    ))

    last_ring = (len(drop_rings) - 1) * side_count

    for i in range(side_count):
        next_i = (i + 1) % side_count
        face_counts.append(3)
        face_connects.extend([top_center, next_i, i])

        face_counts.append(3)
        face_connects.extend([bottom_center, last_ring + i, last_ring + next_i])

    mesh_fn = om.MFnMesh()
    mesh_obj = mesh_fn.create(vertices, face_counts, face_connects)
    drop = om.MFnDagNode(mesh_obj).fullPathName()
    drop = cmds.rename(drop, f"{PFX}Tree_{int(cnt):03d}_leaf_{int(leaf_num):02d}_drop_{int(drop_num):02d}_GEO")

    assign_shader(drop, leaf_shader)
    cmds.parent(drop, tree_grp)
    cmds.select(drop, replace=True)
    cmds.polySoftEdge(angle=100)
    cmds.DeleteHistory()

    return drop


def mk_leaves(cnt, curve_points, tree_grp, shaders, bark_shader):
    # Add 2 to 4 bowl leaves on the middle and lower trunk.
    leaf_shaders = [shaders["leaf_a"], shaders["leaf_b"], shaders["leaf_c"]]
    leaf_count = randint(2, 4)
    start_angle = uniform(0.0, math.tau)

    for leaf_num in range(1, leaf_count + 1):
        if leaf_count == 1:
            path_amount = 0.52
        else:
            path_amount = 0.34 + (leaf_num - 1) * (0.34 / float(leaf_count - 1))

        path_amount = path_amount + uniform(-0.045, 0.045)
        path_amount = max(0.30, min(0.70, path_amount))

        branch_angle = start_angle + math.tau * (leaf_num - 1) / float(leaf_count)
        branch_angle = branch_angle + uniform(-0.28, 0.28)

        trunk_pos = sample_curve_points(curve_points, path_amount)
        leaf_shader = choice(leaf_shaders)
        leaf_anchor, y_rotation = mk_leaf_branch(cnt, leaf_num, trunk_pos, tree_grp, bark_shader, branch_angle)
        mk_bowl_leaf(cnt, leaf_num, leaf_anchor, y_rotation, tree_grp, leaf_shader)


##########################################################################################
# TOP TENDRILS
##########################################################################################

def mk_top_tendrils(cnt, curve_points, top_radius, tree_grp, bark_shader):
    # Add several branching twigs from one shared top area.
    top_pos = curve_points[-1]
    top_tangent = get_curve_tangent(curve_points, 1.0)
    top_normal, top_binormal = get_curve_frame(curve_points, 1.0)
    tendril_count = randint(6, 9)
    start_phase = uniform(0.0, math.tau)

    for tendril_num in range(1, tendril_count + 1):
        angle = start_phase + math.tau * (tendril_num - 1) / float(tendril_count)
        angle = angle + uniform(-0.45, 0.45)
        length = uniform(0.95, 1.65)
        height = uniform(0.25, 0.90)
        curl_a = uniform(-0.75, 0.75)
        curl_b = uniform(-0.95, 0.95)

        root_dir = vec_normalize(vec_add(
            vec_scale(top_normal, math.cos(angle)),
            vec_scale(top_binormal, math.sin(angle)),
        ))
        bend_dir_a = vec_normalize(vec_add(
            vec_scale(top_normal, math.cos(angle + curl_a)),
            vec_scale(top_binormal, math.sin(angle + curl_a)),
        ))
        bend_dir_b = vec_normalize(vec_add(
            vec_scale(top_normal, math.cos(angle + curl_b)),
            vec_scale(top_binormal, math.sin(angle + curl_b)),
        ))
        end_dir = vec_normalize(vec_add(
            vec_scale(top_normal, math.cos(angle + curl_b * 1.20)),
            vec_scale(top_binormal, math.sin(angle + curl_b * 1.20)),
        ))

        start = offset_point(top_pos, top_tangent, -uniform(0.18, 0.28), root_dir, top_radius * 0.05)
        fork = offset_point(top_pos, top_tangent, uniform(0.04, 0.13), root_dir, top_radius * 0.30)
        bend_a = offset_point(top_pos, top_tangent, height * 0.38 + uniform(-0.06, 0.10), bend_dir_a, length * 0.38)
        bend_b = offset_point(top_pos, top_tangent, height * 0.70 + uniform(-0.10, 0.12), bend_dir_b, length * 0.72)
        end = offset_point(top_pos, top_tangent, height + uniform(-0.04, 0.20), end_dir, length)

        tendril_curve = cmds.curve(
            degree=3,
            point=[start, fork, bend_a, bend_b, end],
            name=f"{PFX}Tree_{int(cnt):03d}_tendril_{int(tendril_num):02d}_CRV",
        )

        profile_curve = cmds.circle(
            name=f"{PFX}Tree_{int(cnt):03d}_tendrilProfile_{int(tendril_num):02d}_CRV",
            center=(0, 0, 0),
            normal=top_tangent,
            radius=uniform(0.065, 0.095),
            sections=10,
            constructionHistory=False,
        )[0]
        cmds.move(start[0], start[1], start[2], profile_curve)

        surface_result = cmds.extrude(
            profile_curve,
            tendril_curve,
            n=f"{PFX}Tree_{int(cnt):03d}_tendril_{int(tendril_num):02d}_SURF",
            ch=False,
            rn=False,
            po=0,
            et=2,
            ucp=True,
            fpt=True,
            upn=True,
            ro=0,
            sc=uniform(0.18, 0.30),
        )
        tendril_surface = surface_result[0]

        poly_result = cmds.nurbsToPoly(
            tendril_surface,
            n=f"{PFX}Tree_{int(cnt):03d}_tendril_{int(tendril_num):02d}_GEO",
            ch=False,
            f=2,
            pt=1,
            ut=1,
            un=10,
            vt=1,
            vn=12,
        )
        tendril_geo = poly_result[0]
        tendril_geo = cmds.rename(tendril_geo, f"{PFX}Tree_{int(cnt):03d}_tendril_{int(tendril_num):02d}_GEO")
        assign_shader(tendril_geo, bark_shader)

        cmds.delete(profile_curve)
        cmds.delete(tendril_surface)
        cmds.parent(tendril_curve, tendril_geo, tree_grp)

        cmds.select(tendril_geo, replace=True)
        cmds.polySoftEdge(angle=80)
        cmds.DeleteHistory()

        if tendril_num % 2 == 0:
            fork_angle = angle + choice([-1, 1]) * uniform(0.45, 0.80)
            fork_dir = vec_normalize(vec_add(
                vec_scale(top_normal, math.cos(fork_angle)),
                vec_scale(top_binormal, math.sin(fork_angle)),
            ))
            small_start = bend_b
            small_mid = offset_point(bend_b, top_tangent, uniform(-0.04, 0.12), fork_dir, length * 0.18)
            small_end = offset_point(bend_b, top_tangent, uniform(-0.10, 0.16), fork_dir, length * 0.38)
            small_tangent = vec_normalize(vec_sub(small_mid, small_start))
            small_curve = cmds.curve(
                degree=2,
                point=[small_start, small_mid, small_end],
                name=f"{PFX}Tree_{int(cnt):03d}_tendrilFork_{int(tendril_num):02d}_CRV",
            )
            small_profile = cmds.circle(
                name=f"{PFX}Tree_{int(cnt):03d}_tendrilForkProfile_{int(tendril_num):02d}_CRV",
                center=(0, 0, 0),
                normal=small_tangent,
                radius=uniform(0.025, 0.040),
                sections=8,
                constructionHistory=False,
            )[0]
            cmds.move(small_start[0], small_start[1], small_start[2], small_profile)
            small_surface = cmds.extrude(
                small_profile,
                small_curve,
                n=f"{PFX}Tree_{int(cnt):03d}_tendrilFork_{int(tendril_num):02d}_SURF",
                ch=False,
                rn=False,
                po=0,
                et=2,
                ucp=True,
                fpt=True,
                upn=True,
                ro=0,
                sc=uniform(0.20, 0.35),
            )[0]
            small_poly = cmds.nurbsToPoly(
                small_surface,
                n=f"{PFX}Tree_{int(cnt):03d}_tendrilFork_{int(tendril_num):02d}_GEO",
                ch=False,
                f=2,
                pt=1,
                ut=1,
                un=8,
                vt=1,
                vn=8,
            )[0]
            small_poly = cmds.rename(small_poly, f"{PFX}Tree_{int(cnt):03d}_tendrilFork_{int(tendril_num):02d}_GEO")
            assign_shader(small_poly, bark_shader)
            cmds.delete(small_profile)
            cmds.delete(small_surface)
            cmds.parent(small_curve, small_poly, tree_grp)
            cmds.select(small_poly, replace=True)
            cmds.polySoftEdge(angle=80)
            cmds.DeleteHistory()


def mk_top_canopy(cnt, curve_points, tree_grp, shaders):
    # Build a clustered crown from many simple round forms.
    top_pos = curve_points[-1]
    canopy_shaders = [shaders["canopy_a"], shaders["canopy_b"], shaders["canopy_c"]]
    canopy_shader = choice(canopy_shaders)
    canopy_grp = cmds.group(empty=True, name=f"{PFX}Tree_{int(cnt):03d}_canopy_GRP")
    cmds.parent(canopy_grp, tree_grp)

    blob_count = randint(24, 34)
    canopy_radius = uniform(1.45, 1.95)
    center_y = top_pos[1] + uniform(0.82, 1.08)

    for blob_num in range(1, blob_count + 1):
        ring_amount = math.sqrt(uniform(0.0, 1.0))
        angle = uniform(0.0, math.tau)
        ring_radius = canopy_radius * ring_amount
        dome_amount = 1.0 - ring_amount

        x_pos = top_pos[0] + math.cos(angle) * ring_radius
        z_pos = top_pos[2] + math.sin(angle) * ring_radius
        y_pos = center_y + dome_amount * uniform(0.28, 0.58) + uniform(-0.10, 0.10)

        if ring_amount > 0.72:
            y_pos = y_pos - uniform(0.16, 0.32)

        base_size = uniform(0.24, 0.42) * (1.12 - ring_amount * 0.18)
        blob = cmds.polySphere(
            n=f"{PFX}Tree_{int(cnt):03d}_canopyBlob_{int(blob_num):02d}_GEO",
            r=1,
            sx=10,
            sy=8,
            ch=False,
        )[0]
        cmds.move(x_pos, y_pos, z_pos, blob)
        cmds.scale(
            base_size * uniform(1.05, 1.55),
            base_size * uniform(0.72, 1.08),
            base_size * uniform(1.05, 1.55),
            blob,
        )
        cmds.rotate(uniform(-8, 8), uniform(0, 360), uniform(-8, 8), blob)
        assign_shader(blob, canopy_shader)
        cmds.parent(blob, canopy_grp)
        cmds.select(blob, replace=True)
        cmds.polySoftEdge(angle=100)
        cmds.DeleteHistory()

    return canopy_grp


##########################################################################################
# TREE ASSEMBLY
##########################################################################################

def mk_tree(cnt, vertex, shaders):
    # Create one complete tree at one selected vertex.
    base_pos = find_xyz_pos(vertex)
    tree_grp = cmds.group(empty=True, name=f"{PFX}Tree_{int(cnt):03d}_GRP")
    cmds.xform(tree_grp, worldSpace=True, pivots=base_pos)

    bark_shader = choice([shaders["bark_a"], shaders["bark_b"], shaders["bark_c"]])
    trunk, guide_curve, curve_points, top_radius, side_count = mk_trunk(cnt, tree_grp, base_pos, bark_shader)

    mk_trunk_top_cap(cnt, curve_points, top_radius, side_count, tree_grp, bark_shader)
    mk_top_tendrils(cnt, curve_points, top_radius, tree_grp, bark_shader)
    mk_top_canopy(cnt, curve_points, tree_grp, shaders)
    mk_leaves(cnt, curve_points, tree_grp, shaders, bark_shader)

    return tree_grp


def place_tree(tree, vertex):
    # Randomize the whole tree around the selected point.
    base_pos = find_xyz_pos(vertex)
    cmds.xform(tree, worldSpace=True, pivots=base_pos)
    cmds.rotate(0, uniform(0, 359), 0, tree, relative=True)
    cmds.scale(
        uniform(0.55, 0.92),
        uniform(0.68, 1.12),
        uniform(0.55, 0.92),
        tree,
        relative=True,
    )

    cmds.select(tree, replace=True)
    cmds.DeleteHistory()


def mk_sun_light():
    # Add one warm directional light to work like sunlight.
    sun = cmds.directionalLight(name=PFX + "sun_DIR_LGT", intensity=3.0)
    cmds.setAttr(sun + ".color", 1.0, 0.92, 0.78, type="double3")
    sun_transform = cmds.listRelatives(sun, parent=True)[0]
    cmds.rotate(-50, 42, 0, sun_transform)
    return sun_transform


def mk_hdri_skydome():
    # Create the HDRI skydome light.
    hdri_path = HDRI_PATH

    skydome_shape = cmds.shadingNode("aiSkyDomeLight", asLight=True, name=PFX + "hdri_skyDomeShape")
    cmds.setAttr(skydome_shape + ".intensity", 2.6)

    if cmds.attributeQuery("exposure", node=skydome_shape, exists=True):
        cmds.setAttr(skydome_shape + ".exposure", 0.9)

    if cmds.attributeQuery("camera", node=skydome_shape, exists=True):
        cmds.setAttr(skydome_shape + ".camera", 1)

    if os.path.exists(hdri_path):
        image_node = cmds.shadingNode("aiImage", asTexture=True, name=PFX + "hdri_image")
        cmds.setAttr(image_node + ".filename", hdri_path, type="string")
        cmds.connectAttr(image_node + ".outColor", skydome_shape + ".color", force=True)

    return PFX + "hdri_skyDome"


def set_render_settings():
    # Use Arnold so the skydome can render as the scene environment.
    if cmds.objExists("defaultRenderGlobals"):
        cmds.setAttr("defaultRenderGlobals.currentRenderer", "arnold", type="string")


##########################################################################################
# MAIN
##########################################################################################

def main():
    clean_up()

    selected_points = get_points()
    shaders = mk_all_shaders()
    forest_grp = cmds.group(empty=True, name=FOREST_GRP)

    for count, vert in enumerate(selected_points, 1):
        curr_tree = mk_tree(count, vert, shaders)
        place_tree(curr_tree, vert)
        cmds.parent(curr_tree, forest_grp)

    sun_light = mk_sun_light()
    cmds.parent(sun_light, forest_grp)
    hdri_light = mk_hdri_skydome()

    if hdri_light:
        cmds.parent(hdri_light, forest_grp)

    set_render_settings()
    cmds.select(forest_grp, replace=True)


main()
