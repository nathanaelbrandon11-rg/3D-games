#---------------------------------------------IMPORTS---------------------------------------------#
from pathlib import Path
from direct.showbase.ShowBase import ShowBase
from panda3d.core import (
    DirectionalLight,
    AmbientLight,
    Vec3,
    Point3,
    BitMask32,
    TextNode,
    WindowProperties,
    CollisionTraverser,
    CollisionNode,
    CollisionBox,
    CollisionRay,
    CollisionHandlerQueue,
)
from direct.gui.OnscreenImage import OnscreenImage
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import TransparencyAttrib
from direct.task import Task
from panda3d.core import CollisionTraverser, CollisionNode, CollisionBox, CollisionRay, CollisionHandlerQueue



#------------------------------------VARIABLES------------------------------------#
SHELL_SIZE = 0.1
MOVEMENT_SPEED = 18.0
SPEED_ADJUSTMENT = 110.0
FINE_SPEED_ADJUSTMENT = 0.01
MIN_SPEED_STEP = 0.1
MOUSE_SENSITIVITY = 0.15
MAX_CAMERA_PITCH = 85
INTERACTION_DISTANCE = 20.0
BLOCK_SPACING = 2.0
REDSTONE_MONSTROSITY_SIZE = 1200.0

#---------------------------------------------CLASSES---------------------------------------------#
class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.disableMouse()
        self.model_block = {}
        self.block_positions = {}
        self.block_types = (
            "dirt",
            "grass",
            "sand",
            "stone",
            "blue_shell",
            "redstone_monstrosity",
        )
        self.selected_block = "dirt"
        self.load_model()
        self.atur_cahaya()
        self.crosshair()
        self.buat_dunia()

        # Create only one blue shell.
        self.make_block(0, 0, 1, 'blue_shell', color=(0.2, 0.5, 1.0, 1.0))
        self.camera.setPos(0.5, -16, 8)
        self.camera.lookAt(0.5, 0, 2)
        self.camera_heading, self.camera_pitch, _ = self.camera.getHpr(self.render)
        self.mouse_captured = False
        self.capture_mouse()
        self.accept("escape", self.release_mouse)
        self.accept("mouse1", self.handle_left_click)
        self.accept("mouse3", self.handle_right_click)
        for number, block_type in enumerate(self.block_types, start=1):
            self.accept(str(number), self.select_block, [block_type])
        self.movement_speed = MOVEMENT_SPEED
        self.speed_display = OnscreenText(
            text="",
            parent=self.a2dTopLeft,
            pos=(0.08, -0.08),
            align=TextNode.ALeft,
            scale=0.05,
        )
        self.update_speed_display()
        self.block_display = OnscreenText(
            text="",
            parent=self.a2dTopLeft,
            pos=(0.08, -0.16),
            align=TextNode.ALeft,
            scale=0.05,
        )
        self.update_block_display()
        self.setup_block_sensor()
        self.accept("arrow_up", self.adjust_movement_speed, [SPEED_ADJUSTMENT])
        self.accept("arrow_down", self.adjust_movement_speed, [-SPEED_ADJUSTMENT])
        self.accept("shift-arrow_up", self.adjust_movement_speed, [FINE_SPEED_ADJUSTMENT])
        self.accept("shift-arrow_down", self.adjust_movement_speed, [-FINE_SPEED_ADJUSTMENT])
        self.accept("r", self.reset_movement_speed)
        self.movement_keys = {
            key: False for key in ("w", "a", "s", "d", "e", "q")
        }
        for key in self.movement_keys:
            self.accept(key, self.set_movement_key, [key, True])
            self.accept(f"{key}-up", self.set_movement_key, [key, False])
        self.taskMgr.add(self.update_movement, "update-movement")
        self.taskMgr.add(self.update_mouse_look, "update-mouse-look")

    def _load_model_with_optional_texture(self, model_name, texture_names=None):
        model = self.loader.loadModel(model_name)

        if texture_names is None:
            texture_names = [model_name.replace('.fbx', ''), model_name.replace('.glb', ''), model_name.replace('.obj', '')]

        for name in texture_names:
            for ext in ['.png', '.jpg', '.jpeg', '.tga', '.bmp']:
                texture_path = Path(f"{name}{ext}")
                if texture_path.exists():
                    texture = self.loader.loadTexture(str(texture_path))
                    model.setTexture(texture, 1)
                    return model

        return model

    def load_model(self):
        self.model_block['grass'] = self.loader.loadModel("grass-block.glb")
        self.model_block['stone'] = self.loader.loadModel("stone-block.glb")
        self.model_block['dirt'] = self.loader.loadModel("dirt-block.glb")
        self.model_block['sand'] = self.loader.loadModel("sand-block.glb")

        # Load the exact FBX file path you specified.
        self.model_block['blue_shell'] = self._load_model_with_optional_texture(
            "blue_shell.fbx",
            ["blue_shell", "blue-shell"]
        )
        self.model_block['redstone_monstrosity'] = self.loader.loadModel(
            "redstone_monstrosity.glb"
        )

    def make_block(self, x, y, z, jenis, color=None):
        block_node = self.render.attachNewNode(f"block_{jenis}")
        block_node.setPos(x, y, z)
        block_node.setTag("block_type", jenis)
        shell_model = self.model_block[jenis].instanceTo(block_node)

        bounds_min, bounds_max = self.model_block[jenis].getTightBounds()
        model_scale = 1.0
        model_offset = Vec3(0, 0, 0)
        if jenis == 'blue_shell':
            model_scale = SHELL_SIZE
        elif jenis == 'redstone_monstrosity':
            model_size = bounds_max - bounds_min
            model_scale = REDSTONE_MONSTROSITY_SIZE / max(
                model_size.x,
                model_size.y,
                model_size.z,
            )
            model_offset = -((bounds_min + bounds_max) * 0.5) * model_scale

        if model_scale != 1.0:
            shell_model.setScale(model_scale)
        if model_offset.lengthSquared() > 0:
            shell_model.setPos(model_offset)

        # Keeps its own texture and tints it blue.
        if color is not None or jenis == 'blue_shell':
            shell_model.setColor(color or (0.2, 0.5, 1.0, 1.0))

        collision_center = (
            (bounds_min + bounds_max) * 0.5 * model_scale + model_offset
        )
        collision_half_size = (bounds_max - bounds_min) * (model_scale / 2)
        collision_node = CollisionNode(f"sensor_{jenis}")
        collision_node.setFromCollideMask(BitMask32.allOff())
        collision_node.setIntoCollideMask(BitMask32.bit(1))
        collision_node.addSolid(
            CollisionBox(
                Point3(collision_center),
                collision_half_size.x,
                collision_half_size.y,
                collision_half_size.z,
            )
        )
        collision_path = block_node.attachNewNode(collision_node)
        collision_path.setPythonTag("block", block_node)

        self.block_positions[self.block_position_key(x, y, z)] = block_node
        return block_node

    @staticmethod
    def block_position_key(x, y, z):
        return tuple(round(value, 3) for value in (x, y, z))

    def buat_dunia(self, lebar=10):
        for x in range(lebar):
            for y in range(lebar):
                block_x = (x - (lebar - 1) / 2) * 2
                block_y = (y - (lebar - 1) / 2) * 2
                self.make_block(block_x, block_y, 0, 'dirt')




    def atur_cahaya(self):
        matahari = DirectionalLight('matahari')
        matahari.setColor((0.8, 0.8, 0.8, 1))
        matahari_node = self.render.attachNewNode(matahari)
        matahari_node.setHpr(-45, -45, 0)
        self.render.setLight(matahari_node)

        suasana = AmbientLight('suasana')
        suasana.setColor((0.4, 0.4 , 0.4, 1))
        suasana_node = self.render.attachNewNode(suasana)
        self.render.setLight(suasana_node)

    def crosshair(self):
        self.crosshair_image = OnscreenImage(
            image=str(Path(__file__).with_name("crosshair.png")),
            pos=(0, 0, 0),
            scale=0.05
        )
        self.crosshair_image.setTransparency(TransparencyAttrib.MAlpha)

    def setup_block_sensor(self):
        self.block_sensor = CollisionRay()
        sensor_node = CollisionNode("block_sensor")
        sensor_node.setFromCollideMask(BitMask32.bit(1))
        sensor_node.setIntoCollideMask(BitMask32.allOff())
        sensor_node.addSolid(self.block_sensor)
        self.block_sensor_path = self.camera.attachNewNode(sensor_node)
        self.block_sensor.setFromLens(self.camNode, 0, 0)
        self.block_sensor_queue = CollisionHandlerQueue()
        self.block_sensor_traverser = CollisionTraverser()
        self.block_sensor_traverser.addCollider(
            self.block_sensor_path,
            self.block_sensor_queue,
        )

    def get_targeted_block(self):
        self.block_sensor_queue.clearEntries()
        self.block_sensor_traverser.traverse(self.render)
        self.block_sensor_queue.sortEntries()
        camera_position = self.camera.getPos(self.render)

        for entry in self.block_sensor_queue.getEntries():
            hit_position = entry.getSurfacePoint(self.render)
            if (hit_position - camera_position).length() > INTERACTION_DISTANCE:
                continue

            collision_path = entry.getIntoNodePath()
            block_node = collision_path.getPythonTag("block")
            normal = entry.getSurfaceNormal(self.render)
            normal.normalize()
            axis = max(range(3), key=lambda index: abs(normal[index]))
            face_normal = Vec3(0, 0, 0)
            face_normal[axis] = 1 if normal[axis] >= 0 else -1
            return block_node, face_normal

        return None

    def handle_left_click(self):
        if not self.mouse_captured:
            self.capture_mouse()
            return

        target = self.get_targeted_block()
        if target is None:
            return

        block_node, _ = target
        position = self.block_position_key(*block_node.getPos(self.render))
        self.block_positions.pop(position, None)
        block_node.removeNode()

    def handle_right_click(self):
        if not self.mouse_captured:
            return

        target = self.get_targeted_block()
        if target is None:
            return

        block_node, normal = target
        target_position = block_node.getPos(self.render)
        new_position = target_position + normal * BLOCK_SPACING
        position = self.block_position_key(*new_position)
        if position in self.block_positions:
            return

        self.make_block(*position, self.selected_block)

    def select_block(self, block_type):
        self.selected_block = block_type
        self.update_block_display()

    def update_block_display(self):
        self.block_display.setText(
            f"Block: {self.selected_block}  "
            "(1 dirt, 2 grass, 3 sand, 4 stone, 5 shell, 6 redstone monstrosity)"
        )

    def set_movement_key(self, key, is_pressed):
        self.movement_keys[key] = is_pressed

    def capture_mouse(self):
        if self.mouse_captured or self.win is None:
            return

        self.mouse_captured = True
        properties = WindowProperties()
        properties.setCursorHidden(True)
        if hasattr(self.win, "requestProperties"):
            self.win.requestProperties(properties)
        self.center_mouse_pointer()

    def release_mouse(self):
        if not self.mouse_captured or self.win is None:
            return

        self.mouse_captured = False
        properties = WindowProperties()
        properties.setCursorHidden(False)
        if hasattr(self.win, "requestProperties"):
            self.win.requestProperties(properties)

    def center_mouse_pointer(self):
        if self.win is not None and hasattr(self.win, "movePointer"):
            self.win.movePointer(
                0,
                self.win.getXSize() // 2,
                self.win.getYSize() // 2,
            )

    def rotate_camera(self, delta_x, delta_y):
        self.camera_heading -= delta_x * MOUSE_SENSITIVITY
        self.camera_pitch = max(
            -MAX_CAMERA_PITCH,
            min(MAX_CAMERA_PITCH, self.camera_pitch - delta_y * MOUSE_SENSITIVITY),
        )
        self.camera.setHpr(
            self.render,
            self.camera_heading,
            self.camera_pitch,
            0,
        )

    def update_mouse_look(self, task):
        if self.mouse_captured and self.mouseWatcherNode.hasMouse():
            pointer = self.win.getPointer(0)
            center_x = self.win.getXSize() // 2
            center_y = self.win.getYSize() // 2
            delta_x = pointer.getX() - center_x
            delta_y = pointer.getY() - center_y

            if delta_x or delta_y:
                self.rotate_camera(delta_x, delta_y)
                self.center_mouse_pointer()

        return Task.cont

    def adjust_movement_speed(self, percentage):
        step = max(MIN_SPEED_STEP, self.movement_speed * abs(percentage))
        direction = 1 if percentage > 0 else -1
        self.movement_speed = max(0.0, self.movement_speed + direction * step)
        self.update_speed_display()

    def reset_movement_speed(self):
        self.movement_speed = MOVEMENT_SPEED
        self.update_speed_display()

    def update_speed_display(self):
        self.speed_display.setText(
            f"Speed: {self.movement_speed:.2f} units/s  "
            "(Up/Down: +/-10%, Shift: +/-1%, R: reset)"
        )

    def update_movement(self, task):
        forward = self.camera.getQuat(self.render).getForward()
        forward.z = 0
        forward.normalize()

        right = self.camera.getQuat(self.render).getRight()
        right.z = 0
        right.normalize()

        movement = Vec3(0, 0, 0)
        movement += forward * (
            int(self.movement_keys["w"]) - int(self.movement_keys["s"])
        )
        movement += right * (
            int(self.movement_keys["d"]) - int(self.movement_keys["a"])
        )
        movement.z = int(self.movement_keys["e"]) - int(self.movement_keys["q"])

        if movement.lengthSquared() > 0:
            movement.normalize()
            position = self.camera.getPos(self.render)
            self.camera.setPos(
                self.render,
                position + movement * self.movement_speed * task.dt
            )

        return Task.cont







game = Game()

# No extra world loop here, or it would create many shells.
game.run()