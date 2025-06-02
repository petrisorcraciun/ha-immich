from datetime import timedelta
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, CoordinatorEntity
import logging
import asyncio
import json
from urllib.request import Request, urlopen
from urllib.error import URLError, HTTPError
from typing import Any, Dict, Optional
import os
from .const import STATISTICS_ENDPOINT

_LOGGER = logging.getLogger(__name__)

ICONS = None
ICONS_PATH = os.path.join(os.path.dirname(__file__), "icons.json")
def get_icons() -> Dict[str, str]:
    global ICONS
    if ICONS is None:
        with open(ICONS_PATH, encoding="utf-8") as f:
            ICONS = json.load(f)
    return ICONS

def _get_icon(sensor_type: str) -> str:
    return get_icons().get(sensor_type, "mdi:information-outline")

def ensure_api_url(api_url: str) -> str:
    api_url = api_url.rstrip('/')
    if not api_url.endswith('/api'):
        api_url = f"{api_url}/api"
    return api_url

async def fetch_immich_data(api_url: str, api_key: str, timeout: int = 10, retries: int = 3) -> Dict[str, Any]:
    from .const import STATISTICS_ENDPOINT
    api_url = ensure_api_url(api_url)
    headers = {
        "x-api-key": api_key,
        "Accept": "application/json"
    }
    url = f"{api_url}/{STATISTICS_ENDPOINT}"
    req = Request(url, headers=headers)
    loop = asyncio.get_event_loop()
    last_exception = None
    for attempt in range(1, retries + 1):
        try:
            def do_request():
                with urlopen(req, timeout=timeout) as response:
                    return response.read()
            raw = await loop.run_in_executor(None, do_request)
            _LOGGER.debug(f"Immich API raw response: {raw}")
            data = json.loads(raw.decode("utf-8"))

            result = {
                "total_photos": data.get("photos", 0),
                "total_videos": data.get("videos", 0),
                "occupied_space": data.get("usage", 0),
                "occupied_space_photos": data.get("usagePhotos", 0),
                "occupied_space_videos": data.get("usageVideos", 0),
                "attributes": {
                    "total_photos": data.get("photos", 0),
                    "total_videos": data.get("videos", 0),
                    "occupied_space": data.get("usage", 0),
                    "occupied_space_photos": data.get("usagePhotos", 0),
                    "occupied_space_videos": data.get("usageVideos", 0),
                },
                "users": {},
            }

            for user in data.get("usageByUser", []):
                user_id = user.get("userId")
                if not user_id:
                    continue
                result["users"][user_id] = {
                    "userName": user.get("userName", "Unknown"),
                    "photos": user.get("photos", 0),
                    "videos": user.get("videos", 0),
                    "usage": user.get("usage", 0),
                    "usagePhotos": user.get("usagePhotos", 0),
                    "usageVideos": user.get("usageVideos", 0),
                    "quota": user.get("quotaSizeInBytes"),
                }
            return result
        except (URLError, HTTPError, Exception) as e:
            last_exception = e
            _LOGGER.warning(f"Attempt {attempt} failed to fetch data from Immich: {e}")
            await asyncio.sleep(2)
    _LOGGER.error(f"All {retries} attempts failed to fetch data from Immich: {last_exception}")
    return {
        "total_photos": None,
        "total_videos": None,
        "occupied_space": None,
        "occupied_space_photos": None,
        "occupied_space_videos": None,
        "attributes": {"error": str(last_exception) if last_exception else "Unknown error"},
        "users": {},
    }

class ImmichSensor(CoordinatorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, sensor_type: str, name: str, unit: Optional[str] = None) -> None:
        super().__init__(coordinator)
        self.sensor_type = sensor_type
        self._attr_name = name
        self._attr_unique_id = f"immich_{sensor_type}"
        self._attr_unit_of_measurement = unit
        self._attr_icon = _get_icon(sensor_type)

    @property
    def state(self) -> Optional[Any]:
        value = self.coordinator.data.get(self.sensor_type)
        if value is None:
            error = self.coordinator.data.get("attributes", {}).get("error")
            return error or "no data"
        if self.sensor_type in ["occupied_space", "free_space"] and value is not None:
            return round(value / (1024 ** 3), 2)
        return value

    @property
    def unit_of_measurement(self) -> Optional[str]:
        if self.sensor_type in ["occupied_space", "free_space"]:
            return "GB"
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return self.coordinator.data.get("attributes", {})

class ImmichApiStatusSensor(CoordinatorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_name = "Immich API Status"
        self._attr_unique_id = "immich_api_status"
        self._attr_icon = "mdi:cloud-check"

    @property
    def state(self) -> str:
        data = self.coordinator.data
        if data and all(data.get(k) is not None for k in ["total_photos", "total_videos", "occupied_space", "free_space"]):
            return "online"
        return "offline"

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        data = self.coordinator.data or {}
        return {"error": data.get("attributes", {}).get("error", "")}

class ImmichUserSensor(CoordinatorEntity):
    def __init__(self, coordinator: DataUpdateCoordinator, user_id: str, user_name: str, sensor_type: str, name: str, unit: Optional[str] = None, enabled_default: bool = True) -> None:
        super().__init__(coordinator)
        self.user_id = user_id
        self.user_name = user_name
        self.sensor_type = sensor_type
        self._attr_name = name
        self._attr_unique_id = f"immich_user_{user_id}_{sensor_type}"
        self._attr_unit_of_measurement = unit
        self._attr_icon = _get_icon(sensor_type)
        self._attr_enabled = enabled_default

    @property
    def state(self) -> Optional[Any]:
        user = self.coordinator.data.get("users", {}).get(self.user_id, {})
        value = user.get(self.sensor_type)
        if value is None:
            error = self.coordinator.data.get("attributes", {}).get("error")
            return error or "no data"
        if self.sensor_type in ["usage", "usagePhotos", "usageVideos", "quota"] and value is not None:
            return round(value / (1024 ** 3), 2)
        return value

    @property
    def unit_of_measurement(self) -> Optional[str]:
        if self.sensor_type in ["usage", "usagePhotos", "usageVideos", "quota"]:
            return "GB"
        return None

    @property
    def extra_state_attributes(self) -> Dict[str, Any]:
        return {"user_name": self.user_name}

async def async_setup_entry(hass, entry, async_add_entities):
    api_url = entry.data["api_url"]
    api_key = entry.data["api_key"]
    scan_interval = entry.data.get("scan_interval", 5)

    coordinator = DataUpdateCoordinator(
        hass,
        _LOGGER,
        name="immich_data",
        update_method=lambda: fetch_immich_data(api_url, api_key),
        update_interval=timedelta(minutes=scan_interval),
    )

    last_state = hass.data.get("immich_last_state")
    if last_state:
        coordinator.data = last_state

    await coordinator.async_refresh()

    if all(coordinator.data.get(k) is not None for k in ["total_photos", "total_videos", "occupied_space", "occupied_space_photos", "occupied_space_videos"]):
        hass.data["immich_last_state"] = coordinator.data

    sensors = [
        ImmichSensor(coordinator, "total_photos", "Immich Total Photos"),
        ImmichSensor(coordinator, "total_videos", "Immich Total Videos"),
        ImmichSensor(coordinator, "occupied_space", "Immich Occupied Space", unit="GB"),
        ImmichSensor(coordinator, "occupied_space_photos", "Immich Occupied Space Photos", unit="GB"),
        ImmichSensor(coordinator, "occupied_space_videos", "Immich Occupied Space Videos", unit="GB"),
        ImmichApiStatusSensor(coordinator),
    ]

    for user_id, user in coordinator.data.get("users", {}).items():
        user_name = user.get("userName", "Unknown")
        sensors.append(ImmichUserSensor(coordinator, user_id, user_name, "photos", f"Immich {user_name} Photos", enabled_default=False))
        sensors.append(ImmichUserSensor(coordinator, user_id, user_name, "videos", f"Immich {user_name} Videos", enabled_default=False))
        sensors.append(ImmichUserSensor(coordinator, user_id, user_name, "usage", f"Immich {user_name} Occupied Space", unit="GB", enabled_default=False))
        sensors.append(ImmichUserSensor(coordinator, user_id, user_name, "usagePhotos", f"Immich {user_name} Occupied Space Photos", unit="GB", enabled_default=False))
        sensors.append(ImmichUserSensor(coordinator, user_id, user_name, "usageVideos", f"Immich {user_name} Occupied Space Videos", unit="GB", enabled_default=False))
        if user.get("quota") is not None:
            sensors.append(ImmichUserSensor(coordinator, user_id, user_name, "quota", f"Immich {user_name} Quota", unit="GB", enabled_default=False))

    async_add_entities(sensors)