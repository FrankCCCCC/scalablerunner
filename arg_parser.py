import argparse
from dataclasses import dataclass, asdict, is_dataclass
import json
import os
from typing import Any, Dict, List, Union, Tuple


@dataclass
class DummyClass:
    """
    Just an empty class
    """

    pass


def yield_default(
    config: Union[dataclass, dict], return_dict: bool = False
) -> dataclass:
    config_dict: dict = {}
    res_dataclass: dataclass = DummyClass()

    if is_dataclass(config):
        config_dict = asdict(config)
    for key, val in config_dict.items():
        setattr(res_dataclass, key, val)

    if return_dict:
        return asdict(res_dataclass)
    return res_dataclass


@dataclass
class ArgParser:
    ARGS_EXPORT: str = "export"
    ARGS_DEFAULT: str = "default"
    ARGS_CHOICES: str = "choices"
    ARGS_HELP: str = "help"
    RECEIVE_ARGS_MODE_DEFAULT: str = "AS_DEFAULT"
    RECEIVE_ARGS_MODE_CONFIG: str = "AS_CONFIG"

    VERBOSE_NO: int = 0
    VERBOSE_WARNING: int = 1
    VERBOSE_INFO: int = 2

    def __init__(
        self,
        config_key: str = None,
        config: Union[dict, dataclass] = None,
        file_name=None,
        verbose: int = 0,
    ):
        # self.__config: dataclass = config
        self.__config_dict: dict = {}
        self.__file_name: str = file_name
        self.__verbose: int = verbose
        if (config_key is not None) and (config is not None):
            self.add(config_key=config_key, config=config)

    @staticmethod
    def __rm_keys_from_dict(d: dict, keys: Union[List[object], object]):
        if isinstance(keys, (list, tuple)):
            for key in keys:
                del d[key]
        else:
            del d[key]
        return d

    def __add_args(
        self, parser: argparse.ArgumentParser, key: str, val: dict, mode: str
    ):
        """
        Add arguement to the parser.

        Args:
        - parser: An instance of argparse.ArgumentParser
        - key: The key of the config
        - val: The value of the config
        - mode: The mode of adding the arguement, should be one of ArgParser.RECEIVE_ARGS_MODE_CONFIG or ArgParser.RECEIVE_ARGS_MODE_DEFAULT
        Returns:
        - The parser with the added arguement
        """
        if mode == ArgParser.RECEIVE_ARGS_MODE_CONFIG:
            if self.__verbose > ArgParser.VERBOSE_WARNING:
                print(f"Add arguement: --{key}: {val}")
            # rm_val: dict = ArgParser.__rm_keys_from_dict(d=val, keys=[ArgParser.ARGS_HELP])
            # if ArgParser.ARGS_HELP in val:
            #     parser.add_argument(f'--{key}', help=val[ArgParser.ARGS_HELP], **rm_val)
            parser.add_argument(f"--{key}", **val)
        elif mode == ArgParser.RECEIVE_ARGS_MODE_DEFAULT:
            if self.__verbose > ArgParser.VERBOSE_WARNING:
                print(f"Add arguement: --{key}: default: {val}")
            parser.add_argument(f"--{key}", default=val)
        else:
            raise NotImplementedError()
        return parser

    @staticmethod
    def __default_help_choice(config: dict):
        if ArgParser.ARGS_CHOICES in config:
            config[
                ArgParser.ARGS_HELP
            ] += f", choice: {str(config[ArgParser.ARGS_CHOICES])}"
        return config

    @staticmethod
    def __default_help_default(config: dict):
        if ArgParser.ARGS_DEFAULT in config:
            config[
                ArgParser.ARGS_HELP
            ] += f", default: {str(config[ArgParser.ARGS_DEFAULT])}"
        return config

    def receive_args(
        self,
        config_key: str,
        mode: str = RECEIVE_ARGS_MODE_CONFIG,
        help_choice: bool = True,
        help_default: bool = True,
        *args,
        **kwargs,
    ):
        """
        Receive command line arguments and update the config accordingly.

        Args:
        - config_key: The key of the config
        - mode: The mode of receiving the arguement, should be one of ArgParser.RECEIVE_ARGS_MODE_CONFIG or ArgParser.RECEIVE_ARGS_MODE_DEFAULT
        - help_choice: Whether to add the help message of the choices of the arguement
        - help_default: Whether to add the help message of the default value of the arguement
        - *args, **kwargs: The arguments and key-value arguments to be passed to argparse.ArgumentParser

        Returns:
        - The instance of ArgParser
        """
        if config_key is None:
            raise ValueError("config_key should not be None")
        if config_key not in self.__config_dict:
            raise ValueError(
                f"config_key: {config_key} should be in the config_dict: {self.__config_dict.keys()}"
            )

        config_dict = self.__config_dict[config_key]

        default_vals: dict = {}
        parser = argparse.ArgumentParser(args, kwargs)
        # print(f"config_dict: {config_dict}")
        for key, val in config_dict.items():
            if val is None:
                raise ValueError(f"val should not be None, key: {key}, val: {val}")
            # print(f"key: {key}, val: {val}")
            if mode == ArgParser.RECEIVE_ARGS_MODE_CONFIG:
                if isinstance(val, dict) and ArgParser.ARGS_EXPORT in val:
                    if val[ArgParser.ARGS_EXPORT]:
                        del val[ArgParser.ARGS_EXPORT]
                        # parser.add_argument('--test_tmp', default='test_tmp')
                        val = self.__default_help_default(config=val)
                        val = self.__default_help_choice(config=val)
                        parser = self.__add_args(
                            parser=parser,
                            key=key,
                            val=val,
                            mode=ArgParser.RECEIVE_ARGS_MODE_CONFIG,
                        )
                    else:
                        default_vals[key] = val[ArgParser.ARGS_DEFAULT]
                else:
                    default_vals[key] = val
            elif mode == ArgParser.RECEIVE_ARGS_MODE_DEFAULT:
                default_vals[key] = val

        parse_args = parser.parse_args()
        if not isinstance(parse_args, dict):
            parse_args: dict = parse_args.__dict__
        updated_config: dict = ArgParser.default_update_rule(default_vals, parse_args)
        # print(f"-> default_vals: {default_vals}")
        # print(f"-> parse_args: {parse_args}")
        # print(f"-> updated_config: {updated_config}")
        self.__config_dict[config_key] = updated_config
        # print(f"__config_dict: {self.__config_dict}")
        return self

    def load(
        self,
        file_name: str | None = None,
        config_key: str | None = None,
        not_exist_ok: bool = True,
    ) -> "ArgParser":
        """
        Load config from a file and update the config accordingly.

        Args:
        - file_name (str | None): The file name to be loaded
        - config_key (str | None): The key of the config
        - not_exist_ok (bool): Whether to raise FileNotFoundError if the file does not exist

        Returns:
        - The instance of ArgParser
        """
        if file_name is None:
            file_name = self.__file_name

        try:
            with open(file_name, "r", encoding="utf-8") as f:
                data: dict[str, Any] = json.load(f)
        except FileNotFoundError as file_not_found:
            if not_exist_ok:
                data: dict[str, Any] = {}
            else:
                raise FileNotFoundError(
                    f"file: {file_name} not found"
                ) from file_not_found

        if config_key is None:
            config_key = file_name

        self.__config_dict[config_key] = data

        return self

    def save(
        self, file_name: str = None, config_key: str = None, overwrite: bool = True
    ):
        """
        Save the configuration to a file.

        Args:
        - file_name (str, optional): The name of the file where the config will be saved. Defaults to the instance's self.file_name if not provided.
        - config_key (str, optional): The key of the config to save. Defaults to the arguement file_name if not provided.
        - overwrite (bool): Whether to overwrite the file if it already exists. Defaults to True.

        Returns:
        - self: Returns the instance of ArgParser for method chaining.
        """
        if os.path.isfile(file_name) and not overwrite:
            return self

        if file_name is None:
            file_name = self.__file_name

        if config_key is None:
            config_key = file_name

        data = json.dumps(self.__config_dict[config_key], indent=4)
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(data)

        return self

    def add(self, config: Union[dict, dataclass], config_key: str):
        """
        Add a configuration to the parser's internal dictionary.

        Args:
            config (Union[dict, dataclass]): The configuration data to add, which can be a dictionary or a dataclass.
            config_key (str): The key under which the configuration should be stored in the internal dictionary.

        Returns:
            self: Returns the instance of ArgParser for method chaining.

        Raises:
            NotImplementedError: If the config argument is not a dictionary or a dataclass.
        """
        if isinstance(config, dict):
            self.__config_dict[config_key] = config
        elif is_dataclass(config):
            self.__config_dict[config_key] = asdict(config)
        else:
            raise NotImplementedError(
                f"Arguement config should be Dict or dataclass, not {type(config)}"
            )
        return self

    def update(
        self,
        in_config_keys: Union[List[str], Tuple[str]],
        out_config_keys: str,
        update_rule: callable = None,
    ):
        """
        Update a configuration in the parser's internal dictionary.

        Args:
            in_config_keys (Union[List[str], Tuple[str]]): The keys of the configurations that should be updated or used as input to the update rule.
            out_config_keys (str): The key under which the updated configuration should be stored.
            update_rule (callable, optional): The update rule to use. If not provided, a default rule will be used that simply returns the first input configuration.

        Returns:
            self: Returns the instance of ArgParser for method chaining.
        """
        if not isinstance(in_config_keys, (list, tuple)):
            raise TypeError(
                f"The arguement in_config_keys should be list or tuple, not {type(in_config_keys)}"
            )
        if not isinstance(out_config_keys, str):
            raise TypeError(
                f"The arguement out_config_keys should be str, not {type(out_config_keys)}"
            )

        if update_rule is None:
            res = ArgParser.default_update_rule(
                *[self.__config_dict[key] for key in in_config_keys]
            )
        else:
            res = update_rule(*[self.__config_dict[key] for key in in_config_keys])
        self.__config_dict[out_config_keys] = res

        return self

    @staticmethod
    def default_update_rule(*config_ls):
        """
        A default update rule that takes a variable number of configurations and returns the result of merging them in the order they were provided.

        The merge rules are as follows:

        - If the configuration list is empty, raise a ValueError
        - If the configuration list contains only one item, return that item
        - For each configuration in the list, iterate through its items and update the result with the item from the current configuration if the item is not None.

        Args:
            *config_ls (Dict): A variable number of configuration dictionaries to merge.

        Returns:
            Dict: The merged configuration dictionary.

        Raises:
            ValueError: If the configuration list is empty.
        """
        if len(config_ls) == 0:
            raise ValueError("Empty config list, nothing to update")
        if len(config_ls) <= 1:
            return config_ls[0]

        res = config_ls[0]
        for config in config_ls[1:]:
            for key, val in config.items():
                if val is not None:
                    res[key] = val
        return res

    def parse(
        self,
        config_key: str,
        dataclass_type: callable = None,
        return_dict: bool = False,
    ) -> dataclass:
        """
        Parse the configuration stored in the parser's internal dictionary and return a dataclass of the provided type.

        Args:
            config_key (str): The key of the configuration to parse.
            dataclass_type (callable, optional): The type of the dataclass to return. If not provided, the method will return a dictionary.
            return_dict (bool, optional): Whether to return a dictionary instead of a dataclass.

        Returns:
            Union[dataclass, dict]: The parsed configuration as a dataclass or dictionary.

        Raises:
            ValueError: If the config_key is None, or the dataclass_type is None and return_dict is False, or the config_key is not in the internal dictionary.
        """
        if config_key is None:
            raise ValueError("Arguement config shouldn't be None")
        if dataclass_type is None and not return_dict:
            raise ValueError(
                "Arguement dataclass_type is required for returning the dataclass"
            )
        if config_key not in self.__config_dict:
            raise ValueError(
                f"config_key should be add before, added config_key: {self.__config_dict.keys()}"
            )

        res = dataclass_type()
        for key, val in self.__config_dict[config_key].items():
            setattr(res, key, val)
        return res
