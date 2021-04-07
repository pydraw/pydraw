from pydraw import *
import random

PROJECTILE_SPEED = 10
TARGET_SPEED = 5
PARTICLE_SPEED = 15

screen = Screen(800, 600, "Projectile")

launcher = Rectangle(screen, screen.width() / 2, screen.height() - 25, 50, 300)
launcher.move(-launcher.width() / 2, -launcher.height() / 2)

projectiles = []
targets = []
particles = []


def setup_targets():
    x = 35
    for i in range(5):
        target = Rectangle(screen, x * i + 10, 10, 20, 20, Color('red'))
        targets.append(target)


def spawn_explosion(location):
    for i in range(10):
        particle = Oval(screen, location.x(), location.y(), 5, 5, Color.random())
        particle.rotation(random.random() * 360)
        particles.append(particle)


def fire(location):
    # projectile = Oval(screen, launcher.vertices()[0].x(), launcher.vertices()[0].y(), 10, 10, Color('yellow'))
    print(launcher.center().x(), launcher.center().y())
    projectile = Oval(screen, launcher.center().x(), launcher.center().y(), 10, 10, Color('yellow'))
    # projectile.lookat(location)
    projectile.rotation(launcher.rotation())
    projectiles.append(projectile)


def mousedown(button, location):
    fire(location)


def mousemove(location):
    launcher.lookat(screen.mouse())


screen.listen()

setup_targets()
target_direction = +1  # Positive 1

running = True
fps = 1 / 30
while running:
    for projectile in projectiles:
        projectile.forward(PROJECTILE_SPEED)

        if projectile.x() < 0 or projectile.x() + projectile.width() > screen.width():
            projectile.remove()
            projectiles.remove(projectile)
        elif projectile.y() < 0 or projectile.y() + projectile.height() > screen.height():
            projectile.remove()
            projectiles.remove(projectile)

        for target in targets:
            if projectile.overlaps(target):
                spawn_explosion(target.center())
                target.remove()
                targets.remove(target)
                projectile.remove()
                projectiles.remove(projectile)

    if len(targets) == 0:
        print('Game Over!')
        break
    left = targets[0]
    right = targets[len(targets) - 1]
    if left.x() < 0 or right.x() + right.width() > screen.width():
        target_direction = -target_direction
        for target in targets:
            target.move(dy=35)

    for target in targets:
        target.move(dx=target_direction * TARGET_SPEED)

    for particle in particles:
        particle.forward(PARTICLE_SPEED)
        if particle.x() < 0 or particle.x() + particle.width() > screen.width():
            particles.remove(particle)
            particle.remove()
            del particle
        elif particle.y() < 0 or particle.y() + particle.height() > screen.height():
            particles.remove(particle)
            particle.remove()
            del particle
            continue

    screen.update()
    screen.sleep(fps)

screen.stop()
