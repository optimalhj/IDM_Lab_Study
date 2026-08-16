### Introduction

This project is cloned from https://github.com/stdi-lab/MobRef
It is used for my Deep learning Study!

This is the source code for the paper:
**Predictive Mobile Refueling for Agricultural Machinery via Deep Reinforcement Learning**

---

### Dataset

For the data preprocessing and loading, please refer **`Dataset.py`**.

Simply put, you need the trajectories of agricultural machinery and organize the data of each day into the format of dimension **[n, t, pos]**, where

- **n** denotes the number of agricultural machinery in the environment;
- **t** denotes the time steps divided within a day;
- **pos** denotes the position of the agricultural machinery at the corresponding time step. In our original implementation, only the first value of this dimension was adopted, which represents the index in the grid world and can be converted into column and row coordinates in our code.

### Parameter

You can control the parameters via the file **`parameter.py`**, including certain environment parameters, algorithm parameters and other related configurations. For the macro variables marked in uppercase defined in this file, we have adopted a reflection mechanism, which can automatically add these variables as arguments. In other words, any parameter in the file can be controlled through command line arguments.

#### Preparing the bundled public XLSX files

The bundled public archive contains one GPS recording per machine, while this
implementation expects a fixed number of machines per simulated day.  Create a
runnable train/test split with:

```shell
python ./preprocess_trajectory_data.py
```

This writes `data//train.csv`, `data//test.csv`, and metadata.  The
GPS positions are normalised into the environment's grid so the public dataset
can exercise the code path.  Because the source recordings span distinct real
fields, this output must not be interpreted as geographically faithful paper
results.  Supply a co-located, same-day fleet dataset for scientific evaluation.
Choose the input archive and adjust output settings in the configuration block
at the top of `preprocess_trajectory_data.py`.

### Run Train and Test

We have organized both the training code and testing code in a single file **`main_process.py`**, because they share an identical core logic, with only minor differences in runtime data, training enablement status and other aspects depending on the running mode.
Note that MobRef consists of two phases: **Dispatch** and **Reposition**, which are named **EasyMatch** and **Chihaya** respectively in the code. This means you need to conduct training and subsequent testing for the two phases in sequence.
These two phases can be controlled via the parameters **`--dispatch_train_mode`** and **`--reposition_train_mode`**.
The shell script (linux sh) for the complete execution process can be structured as follows:

1. First, train the Dispatch module

   ```shell
   python ./main_process.py --dispatch_method='EasyMatch' --reposition_method='None' --dispatch_train_mode > 'train_dispatch.log'
   ```
2. Then, train the Reposition module

   ```shell
   python ./main_process.py --dispatch_method='EasyMatch' --reposition_method='Chihaya' --reposition_train_mode > 'train_reposition.log'
   ```
3. Finally, perform a unified test for both modules

   ```shell
   python ./main_process.py --dispatch_method='EasyMatch' --reposition_method='Chihaya' > 'test.log'
   ```

### Packages Needed

Only basic PyTorch and NumPy packages are used in MobRef, with the versions listed as follows:

* PyTorch: 2.8.0+cu128
* NumPy: 2.3.3

Note that generally any official release versions of PyTorch and NumPy are compatible and applicable, and the code is not restricted to specific versions.
