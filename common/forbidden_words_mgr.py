# -*- coding: utf-8 -*-
import config


class ForbiddenWordsMgr(object):

    FORBIDDEN_WORDS_SET = set()

    @classmethod
    def get_words(cls):
        forbidden_words_set = cls.FORBIDDEN_WORDS_SET.union(set(config.FORBIDDEN_WORDS_LIST))
        forbidden_words_set = list(forbidden_words_set)
        forbidden_words_set.sort(cmp=lambda x, y: cmp(len(y), len(x)))

        return forbidden_words_set

    @classmethod
    def has_invalid_word(cls, content):
        for shield_word in cls.get_words():
            if content.find(shield_word) >= 0:
                return True

        return False

    @classmethod
    def replace_word(cls, content, replace_word="**"):
        for shield_word in cls.get_words():
            if shield_word and content.find(shield_word) >= 0:
                content = content.replace(shield_word, replace_word)

        return content

