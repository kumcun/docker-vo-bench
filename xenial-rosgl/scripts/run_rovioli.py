import os
import os.path as op
import subprocess
import argparse
import glob
import time
import pandas as pd
import numpy as np
import sequence_abbrev as sa


class RunROVIOLI:
    def __init__(self, opt):
        self.PKG_NAME = "rovioli"
        self.DATA_ROOT = "/data/dataset"
        self.OUTPUT_ROOT = "/data/output/pose"
        self.TEMP_FILE = op.join(self.OUTPUT_ROOT, "rovlioli_temp.csv")
        self.TEST_IDS = list(range(opt.num_test))

    def run_rovioli(self, opt):
        self.check_base_paths()
        commands, configs = self.generate_commands(opt)
        self.execute_commands(commands, configs)

    def check_base_paths(self):
        assert op.isdir(self.DATA_ROOT), "datset dir doesn't exist"
        assert op.isdir(self.OUTPUT_ROOT), "output dir doesn't exist"

    def generate_commands(self, opt):
        if opt.dataset == "all":
            command_makers = [self.tum_vi, self.euroc_mav]
            commands = []
            configs = []
            for cmdmaker in command_makers:
                cmds, cfgs = cmdmaker(opt.seq_idx)
                commands.extend(cmds)
                configs.extend(cfgs)
        elif opt.dataset == "euroc":
            commands, configs = self.euroc_mav(opt.seq_idx)
        elif opt.dataset == "tumvi":
            commands, configs = self.tum_vi(opt.seq_idx)
        else:
            raise FileNotFoundError()

        print("\n===== Total {} runs\n".format(len(commands)))
        return commands, configs

    def execute_commands(self, commands, configs):
        for i in range(3):
            print("start maplab in {} sec".format(3-i))
            time.sleep(1)

        subprocess.Popen(["roscore"])
        time.sleep(3)
        for ci, (cmd, cfg) in enumerate(zip(commands, configs)):
            outfile = cmd[-1]
            os.makedirs(op.dirname(outfile), exist_ok=True)

            print("\n===== RUN ROVIOLI {}/{}\nconfig: {}\ncmd: {}\n"
                  .format(ci+1, len(commands), cfg, cmd))
            if op.isfile(outfile):
                print("This config has already executed, skip it ....")
                continue

            # save result on temp file in realtime
            cmd[-1] = self.TEMP_FILE
            print("command", cmd)
            subprocess.run(cmd)
            self.format_tum_and_savetxt(outfile)
            subprocess.run(["chmod", "-R", "a+rw", self.OUTPUT_ROOT])
            assert op.isfile(outfile), "===== ERROR: output file was NOT created: {}".format(outfile)

        subprocess.run(["pkill", "roscore"])

    def format_tum_and_savetxt(self, outfile):
        data = pd.read_csv(self.TEMP_FILE)
        data = data.values
        assert data.shape[1] == 16, \
            "[ERROR] ROVIOLI saved file in wrong format, {}".format(data.shape)
        data = np.concatenate([np.expand_dims(data[:, 0], 1), data[:, 8:15]], axis=1)
        print("format resulting poses to tum format and save to", outfile)
        np.savetxt(outfile, data, fmt="%1.6f")
        os.remove(self.TEMP_FILE)

    def euroc_mav(self, seq_idx):
        node_name = "run_rovioli_euroc_vo"
        dataset = "euroc_mav"
        return self.create_commands(node_name, dataset, seq_idx)

    def tum_vi(self, seq_idx):
        node_name = "run_rovioli_tumvi_vo"
        dataset = "tum_vi"
        return self.create_commands(node_name, dataset, seq_idx)

    # Usage:
    # rosrun rovioli run_rovioli_scratch
    #       /path/to/dataset/MH_01_easy.bag
    #       output_file
    def create_commands(self, node_name, dataset, seq_idx: int):
        dataset_path = op.join(self.DATA_ROOT, dataset, "bags")
        output_path = op.join(self.OUTPUT_ROOT, dataset)
        if not op.isdir(output_path):
            os.makedirs(output_path)
        sequences = glob.glob(dataset_path + "/*.bag")
        if seq_idx != -1:
            sequences = [sequences[seq_idx]]
        sequences.sort()
        outname = "rovioli_mvio"

        commands = []
        configs = []
        for si, bagfile in enumerate(sequences):
            seq_abbr = sa.sequence_abbrev(dataset, bagfile.split("/")[-1])
            for test_id in self.TEST_IDS:
                output_file = op.join(output_path, "{}_{}_{}.txt".format(outname, seq_abbr, test_id))
                cmd = ["rosrun", self.PKG_NAME, node_name, bagfile, output_file]
                commands.append(cmd)
                conf = {"executer": outname, "dataset": dataset, "seq_name": op.basename(bagfile),
                        "seq_id": si, "test_id": test_id}
                configs.append(conf)
            print("===== command:", " ".join(commands[-1]))
        return commands, configs


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("-d", "--dataset", default="all", type=str, help="dataset name")
    parser.add_argument("-t", "--num_test", default=5, type=int, help="number of tests per sequence")
    parser.add_argument("-s", "--seq_idx", default=-1, type=int,
                        help="int: index of sequence in sequence list, -1 means all")
    opt = parser.parse_args()

    rovioli = RunROVIOLI(opt)
    rovioli.run_rovioli(opt)


if __name__ == "__main__":
    main()
