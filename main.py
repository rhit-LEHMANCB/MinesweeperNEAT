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
bomb_lists = []
training_size = 100
for i in range(training_size):
    bomb_list = Game.get_random_bomb_list(rows, columns, bombs)
    bomb_lists.append(bomb_list)


def eval_genomes(genomes, config):
    ge = []
    genome_list = []
    for i, [genome_id, genome] in enumerate(genomes):
        genome_list.append(genome)
        genome.fitness = 0

        def on_game_over(fit: int, index: int):
            genome_list[index].fitness += fit

        net = neat.nn.FeedForwardNetwork.create(genome, config)
        training_games = []
        for bomb_list in bomb_lists:
            game = Game(rows, columns, i, net, size, bomb_list, on_game_over)
            training_games.append(game)
        ge.append(training_games)

    while len(ge) > 0:
        for g in ge:
            if len(g) > 0:
                for game in g:
                    if game.game_over:
                        g.remove(game)
                    else:
                        game.activate_net()
            else:
                ge.remove(g)


def run(config_path):
    config = neat.config.Config(
        neat.DefaultGenome,
        neat.DefaultReproduction,
        neat.DefaultSpeciesSet,
        neat.DefaultStagnation,
        config_path
    )

    # pop = neat.Population(config)
    pop = neat.Checkpointer.restore_checkpoint('neat-checkpoint-551')

    pop.add_reporter(neat.StdOutReporter(True))
    stats = neat.StatisticsReporter()
    pop.add_reporter(stats)
    pop.add_reporter(neat.Checkpointer(10))

    winner = pop.run(eval_genomes, 50000)

    visualize.draw_net(config, winner, True)
    visualize.plot_stats(stats, ylog=False, view=False)
    visualize.plot_species(stats, view=False)

    net = neat.nn.FeedForwardNetwork.create(winner, config)
    print(f"Best fitness: {winner.fitness}")

    bomb_list = Game.get_random_bomb_list(rows, columns, bombs)
    window = GameWindow(rows, columns, 0, net, size, bomb_list, lambda a, b: None)
    pyglet.app.run()



if __name__ == '__main__':
    local_dir = os.path.dirname(__file__)
    config_path = os.path.join(local_dir, 'config.txt')
    run(config_path)
