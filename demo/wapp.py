from demo.db_models import Foo, Bar
from wapp.wapp import Wapp


class DemoWapp(Wapp):
    class Models:
        foo = Foo
        bar = Bar
