class Voter(object):

    def __init__(self, user_id, mention, lang_code, voted):
        self.id = user_id
        self.mention = mention
        self.lang_code = lang_code
        self.voted = voted