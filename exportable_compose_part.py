from typing import Union


class ExportableComposePart:
    def export_data_dict(self) -> Union[str, int, dict, None]:
        raise NotImplementedError
