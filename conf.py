import yaml
import io
import threading


__conf_instance = None


def conf(*init_params):
    global __conf_instance
    return __conf_instance


def set_conf_instance(inst):
    global __conf_instance
    __conf_instance = inst


class Conf:
    def __enter__(self):
        with open("config.yaml", 'r') as infile:
            self.conf = yaml.safe_load(infile)
        set_conf_instance(self)
        return self

    def __exit__(self, type, value, traceback):
        with io.open('config.yaml', 'w', encoding='utf8') as outfile:
            yaml.dump(self.conf, outfile)
        set_conf_instance(None)

    def __getitem__(self, key):
        return self.conf[key]

    def __setitem__(self, key, item):
        self.conf[key] = item
