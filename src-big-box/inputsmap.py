import configparser
import sys

import log

CONFIG_FN = "inputsmap.cfg"


class Entry:
	def __init__(self):
		self.fixed = None

		self.p = None
		self.k = None


class InputsMap:
	def __init__(self):
		data = configparser.ConfigParser()
		if len(data.read(CONFIG_FN, encoding='utf8')) != 1:
			print(f"Failed to read config file '{CONFIG_FN}'")
			sys.exit(1)

		self.__map = dict()
		for tp in data.sections():
			for tk in data[tp]:
				try:
					tp_int = int(tp)
					pmap = self.__map.get(tp_int)
					if pmap is None:
						pmap = dict()
						self.__map[tp_int] = pmap

					tk_int = int(tk)

					s = data[tp][tk].strip().lower()
					if s == "off":
						e = Entry()
						e.fixed = False
						pmap[tk_int] = e
					else:
						sa = s.split(":")
						if len(sa) != 2:
							raise RuntimeError(f"incorrect mapping entry syntax: {s}")
						e = Entry()
						e.p = int(sa[0])
						e.k = int(sa[1])
						pmap[tk_int] = e
					
				except Exception as e:
					log.error(f"Inputs map entry syntax error in {tp}/{tk}")

	def apply(self, src):
		s_dict = dict()
		for sPlacement in src:
			p = sPlacement["placement"]
			s_dict_entry = s_dict.get(p)
			if s_dict_entry is None:
				s_dict_entry = dict()
				s_dict[p] = s_dict_entry
			for sKey in sPlacement["data"]:
				s_dict_entry[ sKey["key"] ] = sKey["status"]

		r_dict = dict()
		for p, pMapping in self.__map.items():
			r_dict_entry = r_dict.get(p)
			if r_dict_entry is None:
				r_dict_entry = {"placement": p, "data": []}
				r_dict[p] = r_dict_entry
			for k, kMapping in pMapping.items():
				k_entry = {"key": k, "status": False}
				if kMapping.fixed is not None:
					k_entry["status"] = kMapping.fixed
				else:
					s_dict_entry = s_dict.get(kMapping.p)
					if s_dict_entry is not None:
						value = s_dict_entry.get(kMapping.k)
						if value is not None:
							k_entry["status"] = value
				r_dict_entry["data"].append(k_entry)

		r_list = []
		for r_dict_entry in r_dict.values():
			r_list.append(r_dict_entry)

		return r_list
