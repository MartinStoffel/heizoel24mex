# heizoel24mex
Integration of HeizOel24 MEX sensor into Home Assistant

With this integration, you will get the following sensors

<img width="508" height="476" alt="Bildschirmfoto 2025-11-22 um 16 52 58" src="https://github.com/user-attachments/assets/3bc91eb8-38d2-455a-8377-bd90d1987c2d" />

For the Energy dashboard "*Oil free capacity*" and "*Last order price*" can be used. Since oil as such is not supported by the Energy dashboard, the oil free capacity is of device clas GAS.

You can install via HACS by adding this repository or manually by copy creating custom_components/heizoel24mex in your config directory and add the files of the respective directory in this repo.

After that, just add the integration and follow the configuration. 

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=MartinStoffel&repository=heizoel24mex&category=Integration)

Currently only one sensor is expected/supported.
