bl_info = {
    "name": "CSV Ball-Stick Graph",
    "author": "Mridul",
    "version": (1, 1),
    "blender": (2, 80, 0),
    "location": "View3D > Sidebar > CSV Visualizer",
    "description": "Visualize 2D CSV data as a 3D Ball-Stick model",
    "category": "3D View",
}

import bpy
import pandas as pd
from bpy.props import StringProperty, FloatProperty, BoolProperty
from bpy.types import Operator, Panel, PropertyGroup
from bpy_extras.io_utils import ImportHelper
from mathutils import Vector

# ------------- Helper Functions -------------

def create_material(color):
    mat = bpy.data.materials.new(name="Mat")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = color
    return mat

def add_sphere(location, radius, name, color):
    bpy.ops.mesh.primitive_uv_sphere_add(radius=radius, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(create_material(color))
    return obj

def add_cylinder_between(p1, p2, radius, name, color):
    start = Vector(p1)
    end = Vector(p2)
    direction = end - start
    length = direction.length
    location = start + direction / 2

    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=length, location=location)
    obj = bpy.context.active_object
    obj.name = name
    obj.data.materials.append(create_material(color))

    obj.rotation_mode = 'QUATERNION'
    obj.rotation_quaternion = direction.to_track_quat('Z', 'Y')
    return obj

def create_ball_stick_model(df, x_col, y_col, spacing, ball_radius, stick_radius):
    x_vals = df[x_col].astype(float)
    y_vals = df[y_col].astype(float)

    x_min, x_max = x_vals.min(), x_vals.max()
    y_min, y_max = y_vals.min(), y_vals.max()

    norm_x = (x_vals - x_min) / (x_max - x_min) if x_max != x_min else x_vals
    norm_y = (y_vals - y_min) / (y_max - y_min) if y_max != y_min else y_vals

    points = []
    for i, (x, y) in enumerate(zip(norm_x, norm_y)):
        pos = (x * spacing, y * spacing, 0)
        points.append(pos)
        color = (i / len(df), 1 - i / len(df), 0.8, 1)
        add_sphere(pos, ball_radius, f"Ball_{i}", color)

    for i in range(len(points) - 1):
        add_cylinder_between(points[i], points[i + 1], stick_radius, f"Stick_{i}", (0.8, 0.8, 0.8, 1))


# ------------- Properties -------------

class CSVVisualizerProps(PropertyGroup):
    filepath: StringProperty(name="CSV File", subtype='FILE_PATH')
    x_column: StringProperty(name="X Column", default="x")
    y_column: StringProperty(name="Y Column", default="y")
    spacing: FloatProperty(name="Spacing", default=5.0, min=0.1)
    ball_radius: FloatProperty(name="Ball Radius", default=0.2, min=0.01)
    stick_radius: FloatProperty(name="Stick Radius", default=0.05, min=0.005)
    file_loaded: BoolProperty(name="File Loaded", default=False)
    error_message: StringProperty(name="Error Message", default="")


# ------------- Operators -------------

class CSV_OT_LoadFile(Operator, ImportHelper):
    bl_idname = "csv.load_file"
    bl_label = "Load CSV File"
    filename_ext = ".csv"
    filter_glob: StringProperty(default="*.csv", options={'HIDDEN'})

    def execute(self, context):
        props = context.scene.csv_visualizer
        try:
            df = pd.read_csv(self.filepath)
            props.filepath = self.filepath
            props.file_loaded = True
            props.error_message = ""
        except Exception as e:
            props.file_loaded = False
            props.error_message = f"Error reading CSV: {e}"
        return {'FINISHED'}

class CSV_OT_VisualizeGraph(Operator):
    bl_idname = "csv.visualize_graph"
    bl_label = "Visualize Graph"

    def execute(self, context):
        props = context.scene.csv_visualizer
        try:
            df = pd.read_csv(props.filepath)
            if props.x_column not in df.columns or props.y_column not in df.columns:
                self.report({'ERROR'}, f"Column '{props.x_column}' or '{props.y_column}' not found in CSV.")
                return {'CANCELLED'}

            create_ball_stick_model(
                df,
                props.x_column,
                props.y_column,
                props.spacing,
                props.ball_radius,
                props.stick_radius,
            )
            self.report({'INFO'}, "Graph created.")
            return {'FINISHED'}

        except Exception as e:
            self.report({'ERROR'}, f"Failed to visualize: {e}")
            return {'CANCELLED'}


# ------------- UI Panel -------------

class CSV_PT_VisualizerPanel(Panel):
    bl_label = "CSV Ball-Stick Visualizer"
    bl_idname = "CSV_PT_visualizer"
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "CSV Visualizer"

    def draw(self, context):
        layout = self.layout
        props = context.scene.csv_visualizer

        layout.operator("csv.load_file", icon='FILE_FOLDER')

        if props.file_loaded:
            layout.label(text="CSV Loaded: " + bpy.path.basename(props.filepath), icon='CHECKMARK')
            layout.prop(props, "x_column")
            layout.prop(props, "y_column")
            layout.prop(props, "spacing")
            layout.prop(props, "ball_radius")
            layout.prop(props, "stick_radius")
            layout.operator("csv.visualize_graph", icon='GRAPH')
        else:
            if props.error_message:
                layout.label(text=props.error_message, icon='ERROR')


# ------------- Register -------------

classes = (
    CSVVisualizerProps,
    CSV_OT_LoadFile,
    CSV_OT_VisualizeGraph,
    CSV_PT_VisualizerPanel,
)

def register():
    for cls in classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.csv_visualizer = bpy.props.PointerProperty(type=CSVVisualizerProps)

def unregister():
    for cls in reversed(classes):
        bpy.utils.unregister_class(cls)
    del bpy.types.Scene.csv_visualizer

if __name__ == "__main__":
    register()
