# https://github.com/LmeSzinc/AzurLaneAutoScript/blob/master/module/base/filter.py
import re

from module.logger import logger


class Filter:
    def __init__(self, regex, attr, preset=()):
        """
        Args:
            regex: Regular expression.
            attr: Attribute name.
            preset: Build-in string preset.
        """
        if isinstance(regex, str):
            regex = re.compile(regex)
        self.regex = regex
        self.attr = attr
        self.preset = tuple(list(p.lower() for p in preset))
        self.filter_raw = []
        self.filter = []

    def load(self, string):
        """
        Load a filter string, filters are connected with ">"

        There are also tons of unicode characters similar to ">"
        > \u003E correct
        ＞ \uFF1E
        ﹥ \uFE65
        › \u203a
        ˃ \u02c3
        ᐳ \u1433
        ❯ \u276F
        """
        string = str(string)
        string = re.sub(r'[ \t\r\n]', '', string)
        string = re.sub(r'[＞﹥›˃ᐳ❯]', '>', string)
        self.filter_raw = string.split('>')
        self.filter = [self.parse_filter(f) for f in self.filter_raw]

    def is_preset(self, filter):
        return len(filter) and filter.lower() in self.preset

    def apply(self, objs, func=None):
        """
        Args:
            objs (list): List of objects and strings
            func (callable): A function that to filter object.
                Function should receive an object as arguments, and return a bool.
                True means add it to output.

        Returns:
            list: A list of objects and preset strings, such as [object, object, object, 'reset']
        """
        out = []
        seen = set()  # ⚡ 使用集合加速去重检查
        for raw, filter in zip(self.filter_raw, self.filter):
            if self.is_preset(raw):
                raw_lower = raw.lower()
                if raw_lower not in seen:
                    out.append(raw_lower)
                    seen.add(raw_lower)
            else:
                for obj in objs:
                    # ⚡ 使用id()代替obj not in out，O(1) vs O(n)
                    obj_id = id(obj)
                    if obj_id not in seen and self.apply_filter_to_obj(obj=obj, filter=filter):
                        out.append(obj)
                        seen.add(obj_id)

        if func is not None:
            objs, out = out, []
            for obj in objs:
                if isinstance(obj, str):
                    out.append(obj)
                elif func(obj):
                    out.append(obj)

        return out

    def applys(self, objs, funcs):
        """
        Args:
            objs (list): List of objects and strings
            List[func(callable)] : A list of funciton that to filter object.
                Function should receive an object as arguments, and return a bool.
                True means add it to output.

        Returns:
            list: A list of objects and preset strings, such as [object, object, object, 'reset']
        """
        return self.apply(objs, func=lambda x: all(func(x)for func in funcs))

    def apply_filter_to_obj(self, obj, filter):
        """
        Args:
            obj (object):
            filter (list[str]):

        Returns:
            bool: If an object satisfy a filter.
        """

        for attr, value in zip(self.attr, filter):
            if not value:
                continue
            if str(obj.__getattribute__(attr)).lower() != str(value):
                return False

        return True

    def parse_filter(self, string):
        """
        Args:
            string (str):

        Returns:
            list[strNone]:
        """
        string = string.replace(' ', '').lower()
        result = re.search(self.regex, string)

        if self.is_preset(string):
            return [string]

        if result and len(string) and result.span()[1]:
            return [result.group(index + 1) for index, attr in enumerate(self.attr)]
        else:
            logger.warning(f'Invalid filter: "{string}". This selector does not match the regex, nor a preset.')
            # Invalid filter will be ignored.
            # Return strange things and make it impossible to match
            return ['1nVa1d'] + [None] * (len(self.attr) - 1)