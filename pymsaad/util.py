from uuid import uuid4


def get_rand_hex(string_len=8):
    """Basically takes a uuid4, strips the dashes out, and returns a slice from the end."""
    assert isinstance(string_len, int) and string_len > 0
    randos = "".join(str(uuid4()).split('-'))
    assert string_len <= len(randos)
    string_len = -string_len
    return randos[string_len:]


def save_token(token, outfile_path):
    """Assumes you've done all necessary checks. Will overwrite & should not be run more than once per app session."""
    try:
        with open(outfile_path, 'w') as token_file:
            token_file.write(str(token))
        return True
    except:
        return False

class VersionError(BaseException):
    pass