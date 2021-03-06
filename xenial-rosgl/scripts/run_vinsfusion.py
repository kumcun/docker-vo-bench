import os
import os.path as op
import subprocess
import argparse
import glob
import time
import sequence_abbrev as sa


class RunVinsFusion:
    def __init__(self, opt):
        self.PKG_NAME = "vins"
        self.NODE_NAME = "vins_node"
        self.CONFIG_DIR = "/work/vins_ws/src/vins-fusion/config"
        self.DATA_ROOT = "/data/dataset"
        self.OUTPUT_ROOT = "/data/output/pose"
        self.TEST_IDS = list(range(opt.num_test))

    def run_vinsfusion(self, opt):
        self.check_base_paths()
        commands, configs = self.generate_commands(opt)
        self.execute_commands(commands, configs)

    def check_base_paths(self):
        assert op.isdir(self.DATA_ROOT), "datset dir doesn't exist"
        assert op.isdir(self.CONFIG_DIR), "config dir doesn't exist"
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
            print("start VinsFusion in {} sec".format(3-i))
            time.sleep(1)

        subprocess.Popen(["roscore"])
        time.sleep(3)
        for ci, (cmd, cfg) in enumerate(zip(commands, configs)):
            bagfile = cmd[0]
            outfile = cmd[-1]
            os.makedirs(op.dirname(outfile), exist_ok=True)

            print("\n===== RUN VINS-fusion {}/{}\nconfig: {}\ncmd: {}\n"
                  .format(ci+1, len(commands), cfg, cmd))
            if op.isfile(outfile):
                print("This config has already executed, skip it ....")
                continue

            subprocess.Popen(cmd[1:])
            time.sleep(5)
            subprocess.run(["rosbag", "play", bagfile], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            time.sleep(5)
            subprocess.run(["chmod", "-R", "a+rw", self.OUTPUT_ROOT])
            assert op.isfile(outfile), "===== ERROR: output file was NOT created: {}".format(outfile)
        subprocess.run(["pkill", "roscore"])

    # Usage:
    # rosrun vins vins_node
    #       /path/to/xxx_config.yaml
    #       /path/to/outfile
    def euroc_mav(self, seq_idx):
        dataset = "euroc_mav"
        config_path = op.join(self.CONFIG_DIR, "euroc")
        config_files = {"mvio": "euroc_mono_imu_config.yaml",
                        "stereo": "euroc_stereo_config.yaml",
                        "svio": "euroc_stereo_imu_config.yaml"}
        return self.create_commands(dataset, config_path, config_files, seq_idx)

    # Usage:
    # rosrun vins vins_node
    #       /path/to/xxx_config.yaml
    #       /path/to/outfile
    def tum_vi(self, seq_idx):
        dataset = "tum_vi"
        config_path = op.join(self.CONFIG_DIR, "tumvi512")
        config_files = {"mvio": "tumvi_mono_imu_config.yaml",
                        "stereo": "tumvi_stereo_config.yaml",
                        "svio": "tumvi_stereo_imu_config.yaml"}
        return self.create_commands(dataset, config_path, config_files, seq_idx)

    def create_commands(self, dataset, config_path, config_files, seq_idx):
        dataset_path = op.join(self.DATA_ROOT, dataset, "bags")
        output_path = op.join(self.OUTPUT_ROOT, dataset)
        if not op.isdir(output_path):
            os.makedirs(output_path)
        sequences = glob.glob(dataset_path + "/*.bag")
        if seq_idx != -1:
            sequences = [sequences[seq_idx]]
        sequences.sort()
        outprefix = "vinsfs"

        commands = []
        configs = []
        for suffix, conf_file in config_files.items():
            for si, bagfile in enumerate(sequences):
                outname = outprefix + "_" + suffix
                config_file = op.join(config_path, conf_file)
                seq_abbr = sa.sequence_abbrev(dataset, bagfile.split("/")[-1])
                for test_id in self.TEST_IDS:
                    output_file = op.join(output_path, "{}_{}_{}.txt".format(outname, seq_abbr, test_id))
                    cmd = [bagfile, "rosrun", self.PKG_NAME, self.NODE_NAME, config_file, output_file]
                    commands.append(cmd)
                    conf = {"executer": outname, "config": conf_file, "dataset": dataset,
                            "seq_name": op.basename(bagfile), "seq_id": seq_abbr, "test id": test_id}
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

    vins = RunVinsFusion(opt)
    vins.run_vinsfusion(opt)


if __name__ == "__main__":
    main()
