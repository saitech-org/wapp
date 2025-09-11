from demo.db_models import Foo, Bar
from wapp.wapp import Wapp, WappModels

wapp = Wapp(
    models=WappModels({
        "foo": Foo,
        "bar": Bar
    })
)
