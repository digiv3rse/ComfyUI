import os
import time
import logging
import folder_paths
from aiohttp import web
from folder_paths import map_legacy, filter_files_extensions


class ModelFileManager:
    def __init__(self) -> None:
        self.cache: dict[str, tuple[list[dict], float, float]] = {}

    def get_cache(self, key: str, default=None):
        return self.cache.get(key, default)

    def set_cache(self, key: str, value: tuple[list[dict], float, float]):
        self.cache[key] = value

    def clear_cache(self):
        self.cache.clear()

    def add_routes(self, routes):
        @routes.get("/models")
        def list_model_types(request):
            model_types = list(folder_paths.folder_names_and_paths.keys())

            return web.json_response(model_types)

        @routes.get("/models/{folder}")
        async def get_models(request):
            folder = request.match_info.get("folder", None)
            if not folder in folder_paths.folder_names_and_paths:
                return web.Response(status=404)
            files = folder_paths.get_filename_list(folder)
            return web.json_response(files)

        # NOTE: This is an experiment to replace `/models`
        @routes.get("/experiment/models")
        async def get_model_folders(request):
            model_types = list(folder_paths.folder_names_and_paths.keys())
            folder_black_list = ["configs", "custom_nodes"]
            output_folders: list[dict] = []
            for folder in model_types:
                if folder in folder_black_list:
                    continue
                output_folders.append({"name": folder, "folders": folder_paths.get_folder_paths(folder)})
            return web.json_response(output_folders)

        # NOTE: This is an experiment to replace `/models/{folder}`
        @routes.get("/experiment/models/{folder}")
        async def get_all_models(request):
            folder = request.match_info.get("folder", None)
            if not folder in folder_paths.folder_names_and_paths:
                return web.Response(status=404)
            files = self.get_model_file_list(folder)
            return web.json_response(files)

    def get_model_file_list(self, folder_name: str):
        folder_name = map_legacy(folder_name)
        folders = folder_paths.folder_names_and_paths[folder_name]
        output_list: list[dict] = []

        for index, folder in enumerate(folders[0]):
            out = self.cache_model_file_list_(folder)
            if out is None:
                out = self.recursive_search_models_(folder, index)
                self.set_cache(folder, out)
            output_list.extend(out[0])

        return output_list

    def cache_model_file_list_(self, folder: str):
        model_file_list_cache = self.get_cache(folder)

        if model_file_list_cache is not None:
            if not os.path.isdir(folder):
                return None
            if os.path.getmtime(folder) != model_file_list_cache[1]:
                return None
            return model_file_list_cache
        return None

    def recursive_search_models_(self, directory: str, pathIndex: int) -> tuple[list[str], float, float]:
        if not os.path.isdir(directory):
            return [], 0, time.perf_counter()

        excluded_dir_names = [".git"]
        # TODO use settings
        include_hidden_files = False

        result: list[str] = []

        for dirpath, subdirs, filenames in os.walk(directory, followlinks=True, topdown=True):
            subdirs[:] = [d for d in subdirs if d not in excluded_dir_names]
            if not include_hidden_files:
                subdirs[:] = [d for d in subdirs if not d.startswith(".")]
                filenames = [f for f in filenames if not f.startswith(".")]

            filenames = filter_files_extensions(filenames, folder_paths.supported_pt_extensions)

            for file_name in filenames:
                try:
                    relative_path = os.path.relpath(os.path.join(dirpath, file_name), directory)
                    result.append(relative_path)
                except:
                    logging.warning(f"Warning: Unable to access {file_name}. Skipping this file.")
                    continue

        return [{"name": f, "pathIndex": pathIndex} for f in result], os.path.getmtime(directory), time.perf_counter()

    def __exit__(self, exc_type, exc_value, traceback):
        self.clear_cache()
