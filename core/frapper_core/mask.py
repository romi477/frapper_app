def rebuild_string(sentence, mask, wrap='<u>{word}</u>'):
    string = ''
    for flag, word in zip(mask, sentence.split()):
        if int(flag):
            word = wrap.format(word=word)
        string += f'{word} '
    return string
