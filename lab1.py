import tkinter as tk
from tkinter import ttk
from pickle import DEFAULT_PROTOCOL, Pickler, Unpickler
from io import BytesIO

import collections.abc

file_name1 = 'name'
file_name2 = 'price'
file_name3 = 'category'

__all__ = ["Shelf", "BsdDbShelf", "DbfilenameShelf", "open"]

class _ClosedDict(collections.abc.MutableMapping):
    def closed(self, *args):
        raise ValueError('invalid operation on closed shelf')
    __iter__ = __len__ = __getitem__ = __setitem__ = __delitem__ = keys = closed

    def __repr__(self):
        return '<Closed Dictionary>'


class Shelf(collections.abc.MutableMapping):
    def __init__(self, dict, protocol=None, writeback=False,
                 keyencoding="utf-8"):
        self.dict = dict
        if protocol is None:
            protocol = DEFAULT_PROTOCOL
        self._protocol = protocol
        self.writeback = writeback
        self.cache = {}
        self.keyencoding = keyencoding

    def __iter__(self):
        for k in self.dict.keys():
            yield k.decode(self.keyencoding)

    def __len__(self):
        return len(self.dict)

    def __contains__(self, key):
        return key.encode(self.keyencoding) in self.dict

    def get(self, key, default=None):
        if key.encode(self.keyencoding) in self.dict:
            return self[key]
        return default

    def __getitem__(self, key):
        try:
            value = self.cache[key]
        except KeyError:
            f = BytesIO(self.dict[key.encode(self.keyencoding)])
            value = Unpickler(f).load()
            if self.writeback:
                self.cache[key] = value
        return value

    def __setitem__(self, key, value):
        if self.writeback:
            self.cache[key] = value
        f = BytesIO()
        p = Pickler(f, self._protocol)
        p.dump(value)
        self.dict[key.encode(self.keyencoding)] = f.getvalue()

    def __delitem__(self, key):
        del self.dict[key.encode(self.keyencoding)]
        try:
            del self.cache[key]
        except KeyError:
            pass

    def __enter__(self):
        return self

    def __exit__(self, type, value, traceback):
        self.close()

    def close(self):
        if self.dict is None:
            return
        try:
            self.sync()
            try:
                self.dict.close()
            except AttributeError:
                pass
        finally:
            try:
                self.dict = _ClosedDict()
            except:
                self.dict = None

    def __del__(self):
        if not hasattr(self, 'writeback'):
            return
        self.close()

    def sync(self):
        if self.writeback and self.cache:
            self.writeback = False
            for key, entry in self.cache.items():
                self[key] = entry
            self.writeback = True
            self.cache = {}
        if hasattr(self.dict, 'sync'):
            self.dict.sync()

class BsdDbShelf(Shelf):
    def __init__(self, dict, protocol=None, writeback=False,
                 keyencoding="utf-8"):
        Shelf.__init__(self, dict, protocol, writeback, keyencoding)

    def set_location(self, key):
        (key, value) = self.dict.set_location(key)
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())

    def next(self):
        (key, value) = next(self.dict)
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())

    def previous(self):
        (key, value) = self.dict.previous()
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())

    def first(self):
        (key, value) = self.dict.first()
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())

    def last(self):
        (key, value) = self.dict.last()
        f = BytesIO(value)
        return (key.decode(self.keyencoding), Unpickler(f).load())


class DbfilenameShelf(Shelf):
    def __init__(self, filename, flag='c', protocol=None, writeback=False):
        import dbm
        Shelf.__init__(self, dbm.open(filename, flag), protocol, writeback)


def open(filename, flag='c', protocol=None, writeback=False):
    return DbfilenameShelf(filename, flag, protocol, writeback)


class Main(tk.Frame):
    def __init__(self, root):
        super().__init__(root)
        self.init_main()
        self.db = db
        self.view_records()

    def init_main(self):
        toolbar = tk.Frame(bg='#d7d8e0', bd=2)
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self.add_img = tk.PhotoImage(file='add.gif')
        btn_open_dialog = tk.Button(toolbar, text='Добавить товар', command=self.open_dialog, bg='#d7d8e0', bd=0,
                                    compound=tk.TOP, image=self.add_img)
        btn_open_dialog.pack(side=tk.LEFT)

        self.update_img = tk.PhotoImage(file='update.gif')
        btn_edit_dialog = tk.Button(toolbar, text='Редактировать', bg='#d7d8e0', bd=0, image=self.update_img,
                                    compound=tk.TOP, command=self.open_update_dialog)
        btn_edit_dialog.pack(side=tk.LEFT)

        self.delete_img = tk.PhotoImage(file='delete.gif')
        btn_delete = tk.Button(toolbar, text='Удалить позицию', bg='#d7d8e0', bd=0, image=self.delete_img,
                               compound=tk.TOP, command=self.delete_records)
        btn_delete.pack(side=tk.LEFT)

        self.search_img = tk.PhotoImage(file='search.gif')
        btn_search = tk.Button(toolbar, text='Поиск', bg='#d7d8e0', bd=0, image=self.search_img,
                               compound=tk.TOP, command=self.open_search_dialog)
        btn_search.pack(side=tk.LEFT)

        self.tree = ttk.Treeview(self, columns=('ID', 'name', 'category', 'price'), height=15, show='headings')

        self.tree.column('ID', width=30, anchor=tk.CENTER)
        self.tree.column('name', width=350, anchor=tk.CENTER)
        self.tree.column('category', width=70, anchor=tk.CENTER)
        self.tree.column('price', width=150, anchor=tk.CENTER)

        self.tree.heading('ID', text='ID')
        self.tree.heading('name', text='Название товара')
        self.tree.heading('category', text='Цена')
        self.tree.heading('price', text='Категория товара(A, B, C)')

        self.tree.pack()

    def records(self, name, price, category):
        self.db.insert_data(name, price, category)
        self.view_records()

    def view_records(self):
        [self.tree.delete(i) for i in self.tree.get_children()]
        with open(file_name1) as name:
            with open(file_name2) as price:
                with open(file_name3) as category:
                    for key in name:
                        row = [key, name[key], price[key], category[key]]
                        self.tree.insert('', 'end', values=row)

    def update_record(self, name1, price1, category1):
        key = self.tree.set(self.tree.selection()[0], '#1')
        with open(file_name1) as name:
            with open(file_name2) as price:
                with open(file_name3) as category:
                    name[key] = name1
                    price[key] = price1
                    category[key] = category1
        self.view_records()

    def delete_records(self):
        key = self.tree.set(self.tree.selection()[0], '#1')
        with open(file_name1) as name:
            with open(file_name2) as price:
                with open(file_name3) as category:
                    del name[key], price[key], category[key]
        self.view_records()

    def search_records(self, description):
        counter = 1
        keys = []
        with open(file_name1) as name:
            with open(file_name2) as price:
                with open(file_name3) as category:
                    values = name.values()
                    for val in values:
                        if val == description:
                            keys.append(str(counter))
                        counter += 1
                    [self.tree.delete(i) for i in self.tree.get_children()]
                    for key in keys:
                        row = [key, name[key], price[key], category[key]]
                        self.tree.insert('', 'end', values=row)


    def open_dialog(self):
        Child()

    def open_update_dialog(self):
        Update()

    def open_search_dialog(self):
        Search()


class Child(tk.Toplevel):
    def __init__(self):
        super().__init__(root)
        self.init_child()
        self.view = app

    def init_child(self):
        self.title('Добавить товар')
        self.geometry('400x220+400+300')
        self.resizable(False, False)

        label_name = tk.Label(self, text='Название товара:')
        label_name.place(x=50, y=50)
        label_category = tk.Label(self, text='Категория товара:')
        label_category.place(x=50, y=80)
        label_price = tk.Label(self, text='Цена:')
        label_price.place(x=50, y=110)

        self.entry_name = ttk.Entry(self)
        self.entry_name.place(x=200, y=50)

        self.entry_price = ttk.Entry(self)
        self.entry_price.place(x=200, y=110)

        self.combobox = ttk.Combobox(self, values=[u'A', u'B', u'C'])
        self.combobox.current(0)
        self.combobox.place(x=200, y=80)

        btn_cancel = ttk.Button(self, text='Закрыть', command=self.destroy)
        btn_cancel.place(x=300, y=170)

        btn_ok = ttk.Button(self, text='Добавить')
        btn_ok.place(x=220, y=170)
        btn_ok.bind('<Button-1>', lambda event: self.view.records(self.entry_name.get(),
                                                                  self.entry_price.get(),
                                                                  self.combobox.get()))

        self.grab_set()
        self.focus_set()


class Update(Child):
    def __init__(self):
        super().__init__()
        self.init_edit()
        self.view = app

    def init_edit(self):
        self.title('Редактировать данные')
        btn_edit = ttk.Button(self, text='Редактировать')
        btn_edit.place(x=205, y=170)
        btn_edit.bind('<Button-1>', lambda event: self.view.update_record(self.entry_name.get(),
                                                                          self.entry_price.get(),
                                                                          self.combobox.get()))
        self.btn_ok.destroy()


class Search(tk.Toplevel):
    def __init__(self):
        super().__init__()
        self.init_search()
        self.view = app

    def init_search(self):
        self.title('Поиск')
        self.geometry('300x100+400+300')
        self.resizable(False, False)

        label_search = tk.Label(self, text='Поиск')
        label_search.place(x=50, y=20)

        self.entry_search = ttk.Entry(self)
        self.entry_search.place(x=105, y=20, width=150)

        btn_cancel = ttk.Button(self, text='Закрыть', command=self.destroy)
        btn_cancel.place(x=185, y=50)

        btn_search = ttk.Button(self, text='Поиск')
        btn_search.place(x=105, y=50)
        btn_search.bind('<Button-1>', lambda event: self.view.search_records(self.entry_search.get()))
        btn_search.bind('<Button-1>', lambda event: self.destroy(), add='+')


class DB:
    name = open(file_name1)
    if len(name) > 0:
        keys = list(name.keys())
        key = keys[len(name)-1]
    else:
        key = '1'
    price = open(file_name2)
    category = open(file_name3)

    def insert_data(self, name1, price1, category1):
        self.name[self.key] = name1
        self.price[self.key] = price1
        self.category[self.key] = category1
        self.key = str(int(self.key) + 1)


if __name__ == "__main__":
    root = tk.Tk()
    db = DB()
    app = Main(root)
    app.pack()
    root.title("Список покупок")
    root.geometry("600x450+300+200")
    root.resizable(False, False)
    root.mainloop()
