import os.path

import pyglet
import neat

import visualize
from game import Game
from game_window import GameWindow

size = 512
rows = 5
columns = 5
bombs = 5
bomb_list = Game.get_random_bomb_list(rows, columns, bombs)


def eval_genomes(genomes, config):
    games = []
    genome_list = []
    for i, [genome_id, genome] in enumerate(genomes):
        genome_list.append(genome)
        genome.fitness = 0

        def on_game_over(fit: int, index: int):
            genome_list[index].fitness = fit

        net = neat.nn.FeedForwardNetwork.create(genome, config)
        game = Game(rows, columns, i, net, size, bomb_list, on_game_over)
        games.append(game)

    while len(games) > 0:
        for game in games:
            if game.game_over:
                games.remove(game)
            else:
                game.activate_net()


def run(config_path):
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_path
    )

    pop = neat.Population(config)

    pop.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    pop.add_reporter(stats)
    pop.add_reporter(neat.Checkpointer(100))
    winner = pop.run(eval_genomes, 5000)

    visualize.draw_net(config, winner, True)
    visualize.plot_stats(stats, ylog=False, view=False)
    visualize.plot_species(stats, view=False)

    net = neat.nn.FeedForwardNetwork.create(winner, config)
    print(f"Best fitness: {winner.fitness}")

    window = GameWindow(rows, columns, 0, net, size, bomb_list, lambda a, b: None)
    pyglet.app.run()



if __name__ == '__main__':
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config.txt')
    run(config_path)
