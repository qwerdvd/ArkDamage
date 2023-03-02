class Log:
    def __init__(self):
        self.log = ''
        self.buff_list = []
        self.loop_list = []
        self.edge_list = []
        self.final_list = []
        self.damage_list = []
        self.note = ''

    def output(self):
        return self.log

    def write_buff(self, line):
        self.buff_list.append(line)

    def write_loop(self, line):
        self.loop_list.append(line)

    def write_edge(self, line):
        self.edge_list.append(line)

    def write_final(self, line):
        self.final_list.append(line)

    def write_damage(self, line):
        self.damage_list.append(line)

    def write(self, line):
        # 处理成markdown格式
        # self.log += line.replace('_', '\\_').replace('~', '_') + '\n'
        self.log += line + '\n'

    def write_note(self, line):
        if line not in self.note:
            self.log += f'[注记] {line}\n'
            self.note += line + '\n'

    def __str__(self):
        return self.log


class NoLog:
    def write(self, line):
        pass

    def write_note(self, line):
        pass

    def __str__(self):
        return ''
