#---------------------------------------------IMPORTS---------------------------------------------#
from pathlib import Path
from direct.showbase.ShowBase import ShowBase
from panda3d.core import DirectionalLight, AmbientLight








#---------------------------------------------CLASSES---------------------------------------------#
class Game(ShowBase):
    def __init__(self):
        ShowBase.__init__(self)
        self.model_block = {}
        self.load_model()

        # Create only one blue shell.
        self.make_block(0, 0, 0, 'blue_shell', color=(0.2, 0.5, 1.0, 1.0))

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

    def make_block(self, x, y, z, jenis, color=None):
        block_node = self.render.attachNewNode(f"block_{jenis}")
        block_node.setPos(x, y, z)
        shell_model = self.model_block[jenis].instanceTo(block_node)

        # Keeps its own texture and tints it blue.
        if color is not None:
            shell_model.setColor(color)

    def buat_dunia(self, lebar=1):
        # Keep the function, but only generate a single shell.
        self.make_block(0, 0, 0, 'blue_shell', color=(0.2, 0.5, 1.0, 1.0))




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

game = Game()
# No extra world loop here, or it would create many shells.
game.run()