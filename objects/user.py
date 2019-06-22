class User(object):

    def __init__(self, user_id, positions):
        self.id = user_id
        self.positions = self.set_positions(positions)
        self.devices = []

    @staticmethod
    def set_positions(positions):
        temp_dic = {}
        if positions:
            for position in positions:
                temp_dic[position] = True
        return temp_dic
