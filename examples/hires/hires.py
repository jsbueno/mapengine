from mapengine import Scene, simpleloop, Hero, Actor, GameObject


class ImageChanger(GameObject):
    icon_name = "hero"
    move_rate = 4
    def on_over(self, other):
        if isinstance(other, Hero):
            if getattr(other, "_changer_image_name", None) != self.icon_name:
                other._changer_image_name = self.icon_name
                other.image_load(self.icon_name)
                other.base_move_rate = self.move_rate

class Ocean(ImageChanger):
    # hardness = 5
    icon_name = "hero_boat"
    #move_rate = 8

class Desert(ImageChanger):
    icon_name = "hero_desert"

class Forest(ImageChanger):
    icon_name = "hero"

class Ice(ImageChanger):
    icon_name = "hero_ice"
    #move_rate = 12

class Madagascar(Forest):
    def on_over(self, other):
        if isinstance(other, Hero):
            madagascar = Scene("madagascar", display_type="overlay")
            self.controller.load_scene(madagascar)


def main():
    scene = Scene("map0", display_type="overlay", margin=0)
    simpleloop(scene, (800, 600), godmode=False)

main()