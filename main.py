import multiprocessing as mp
from functions import *


def main(args):
    if len(args) > 0:
        data = get_data_from_csv(args[0])
    else:
        data = normalized_data()

    processes = list()
    with mp.Pool(len(data['hosts'])) as pool:
        for device in data['hosts']:
            processes.append(pool.apply_async(start_process, args=(device, data)))

        for proc in processes:
            proc.get()


if __name__ == "__main__":
    args = sys.argv[1:]
    main(args)

