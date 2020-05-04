# kscope-artifact

This repository contains the artifact release for kscope. 

# Datsets

## Store Pings

We have implemented *store pings* both in Python and Ruby. We use Python for our scalability experiments.

* [Ruby](store-pings/ruby)
* [Python](store-pings/python)


## Log parsing
We have used the following [regex rules](log-parsing) to parse the error logs from the Cray Systems. 


# Machine Learning. 

We have implemented the machine-learning using Python. The probabilistic program shows the implementation of the described architecture as an example. The code is shown in a [Jupyter Notebook](kscope-ml-impl/bw-lustre.ipynb). The sample output visualizations can be found in the following [Jupyter Notebook](kscope-ml-impl/Viz.ipynb)

# Related Work
We compare our work with NetBouncer [NSDI 2020]. We implemented NetBouncer and verified its implementation with the authors. The code is located [here](relatedwork/netbouncer).  