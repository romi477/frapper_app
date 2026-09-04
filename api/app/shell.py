# python3 -i .

if __name__ == '__main__':

    from pony.orm import *

    from app.config import config
    from app.db.database import db
    from app.models.phrase_meta import PhraseMeta as M
    from app.models.phrase_pl import PhrasePl as P

    print(
"""
VARIABLES:

    - pony.orm *
    - config
    - db
    - PhraseMeta as M
    - PhrasePl as P
"""
    )
