def setup_style(font_size=8):
    import matplotlib
    matplotlib.use('agg')  # generate postscript output by default
    import matplotlib.pyplot as plt
    from matplotlib import rc

    plt.style.use('classic')
    plt.set_cmap(plt.cm.viridis)

    # rc('text', usetex=True)
    plt.rcParams['axes.grid'] = True
    plt.rcParams['axes.labelpad'] = 0
    plt.rcParams['grid.color'] = 'k'
    plt.rcParams['grid.linestyle'] = ':'
    plt.rcParams['grid.linewidth'] = 0.5

    plt.rcParams['axes.linewidth'] = 1.5
    plt.rcParams['axes.labelweight'] = 'bold'
    plt.rcParams['font.size'] = font_size
    plt.rcParams['axes.labelsize'] = font_size
    plt.rcParams['axes.titlesize'] = font_size
    plt.rcParams['xtick.labelsize'] = font_size - 1
    plt.rcParams['ytick.labelsize'] = font_size - 1
    plt.rcParams['legend.fontsize'] = font_size - 1
    plt.rcParams['figure.titlesize'] = font_size
    # plt.rcParams['savefig.bbox'] = 'tight' # not compatible with animations
    # plt.rcParams['savefig.pad_inches'] : 0.025      # Padding to be used when bbox is set to 'tight'
    plt.rcParams['figure.figsize'] = [3.487, 2.155
                                      ]  # IEEE half column and golden ratio
