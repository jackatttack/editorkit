"""Pythonista 2: scene.

Run this script. The scene module draws games and animations: a Scene
subclass with setup, touches and a frame-by-frame update. Each step shows
its scene in a window beside the code; the last one runs it full screen,
as a game does.
"""
import scene

import editorkit as ek
from editorkit.lessons import Lesson

lesson = Lesson('scene', __file__, emoji='🐍')


def scene_window(stage):
    """A scene shown in a lesson window (a SceneView holds it)."""
    view = scene.SceneView()
    view.scene = stage
    view.flex = 'WH'
    lesson.show_view(view, 'scene', key='lesson-scene')


@lesson.step('A scene and a sprite', docs='scene.SpriteNode')
def sprite():
    """A Scene draws itself: setup() runs once, with self.size known. A
    SpriteNode is a picture placed by its position, measured from the
    bottom left; parent=self puts it in the scene.

    Try it: a ship sits in the middle. Resize the window: did_change_size
    keeps it there."""
    class Stage(scene.Scene):

        def setup(self):
            self.background_color = '#14181d'
            self.ship = scene.SpriteNode('spc:PlayerShip1Orange', parent=self)
            self.did_change_size()

        def did_change_size(self):
            self.ship.position = (self.size.w / 2, self.size.h / 2)

    scene_window(Stage())


@lesson.step('Touches', docs='scene.Scene.touch_began')
def touches():
    """touch_began, touch_moved and touch_ended get a touch with its
    location in the scene. An Action moves the ship there smoothly instead
    of jumping.

    Try it, then tap around the scene."""
    class Stage(scene.Scene):

        def setup(self):
            self.background_color = '#14181d'
            self.ship = scene.SpriteNode('spc:PlayerShip1Orange', parent=self,
                                         position=(self.size.w / 2, self.size.h / 2))

        def touch_began(self, touch):
            x, y = touch.location
            self.ship.run_action(scene.Action.move_to(x, y, 0.4, scene.TIMING_EASE_OUT))

    scene_window(Stage())


@lesson.step('update() runs every frame', docs='scene.Scene.update')
def every_frame():
    """update() runs about 60 times a second. self.t is the time since the
    scene started, so anything worked out from it moves on its own. A
    LabelNode shows text.

    Try it: the ship circles the middle and the label counts frames."""
    class Stage(scene.Scene):

        def setup(self):
            self.background_color = '#14181d'
            self.ship = scene.SpriteNode('spc:PlayerShip1Orange', parent=self, scale=0.6)
            self.label = scene.LabelNode('', font=('Menlo', 15), parent=self)
            self.frames = 0

        def update(self):
            from math import cos, sin
            middle_x, middle_y = self.size.w / 2, self.size.h / 2
            self.ship.position = (middle_x + 80 * cos(self.t), middle_y + 80 * sin(self.t))
            self.ship.rotation = self.t
            self.frames += 1
            self.label.text = '%d frames' % self.frames
            self.label.position = (middle_x, 24)

    scene_window(Stage())


@lesson.step('Actions do the animating', docs='scene.Action')
def actions():
    """Actions animate without any code in update(): move_by, scale_to,
    rotate_by, fade_to and more. sequence runs them in turn, repeat repeats
    one (-1 is for ever).

    Try it: the ship bobs on its own. Tap it to make it spin and grow."""
    class Stage(scene.Scene):

        def setup(self):
            self.background_color = '#14181d'
            self.ship = scene.SpriteNode('spc:PlayerShip1Orange', parent=self,
                                         position=(self.size.w / 2, self.size.h / 2))
            bob = scene.Action.sequence(scene.Action.move_by(0, 20, 0.6, scene.TIMING_EASE_IN_OUT),
                                        scene.Action.move_by(0, -20, 0.6, scene.TIMING_EASE_IN_OUT))
            self.ship.run_action(scene.Action.repeat(bob, -1))

        def touch_began(self, touch):
            self.ship.run_action(scene.Action.sequence(
                scene.Action.group(scene.Action.rotate_by(6.283, 0.5),
                                   scene.Action.scale_to(1.6, 0.25)),
                scene.Action.scale_to(1.0, 0.25)))

    scene_window(Stage())


@lesson.step('Run it as a game', docs='scene.run')
def as_a_game():
    """A finished game ends with scene.run(MyScene()): full screen, with a
    close button. show_fps=True puts the frame rate in a corner.

    Try it: tap to steer the ship. ✕ at the top left closes it, and the
    lesson is still here."""
    class Game(scene.Scene):

        def setup(self):
            self.background_color = '#14181d'
            self.ship = scene.SpriteNode('spc:PlayerShip1Orange', parent=self,
                                         position=(self.size.w / 2, self.size.h / 3))

        def touch_began(self, touch):
            x, y = touch.location
            self.ship.run_action(scene.Action.move_to(x, y, 0.5, scene.TIMING_EASE_OUT))

    scene.run(Game(), show_fps=True)
    return 'Close it with ✕ at the top left.'


lesson.run()