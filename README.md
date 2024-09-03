# Live Wires-X 

## About Yaesu Wires-X

WIRES-X (Wide-coverage Internet Repeater Enhancement System) is an Internet communication system that expands the range of amateur radio communication. It uses an amateur node station connected to the Internet as an access point, allowing users to communicate with other amateur stations worldwide. WIRES-X supports C4FM digital technology, providing high sound quality and clear voice communications even over long distances.

## Docker container
This project is avalable as a Docker container for you to run in your shack, it will run on a Respbery Pi (tested on a 3b, 4 & 5) quite nicly:

- docker run -d -p 80:80 --name live_wires_x --restart=always neonsunset/live_wires_x

you can run this on any port you would like just change the

- docker run -d -p :80 --name live_wires_x --restart=always neonsunset/live_wires_x

You can see the container images on: [https://hub.docker.com/r/neonsunset/live_wires_x](https://hub.docker.com/r/neonsunset/live_wires_x)

## Example site
This is a running example of the docker container image running in Microsoft Azure.
(The docker container running on Azure)[http://wiresx.f2hkgyhbbccbdrbt.ukwest.azurecontainer.io/]

## To run this in a production enviorement from the code rather then the docker image please use the following command: 
- gunicorn -w 4 -b 0.0.0.0:80 app:app

## Why This Site?
I have used the WIRES-X ACTIVE NODE ID list in the yaesu.com website and while it is a good list that is up to date, the user experience is a little lacking, so this site has been put together.

## Age of the data?
Yaasu publishes a list of Wires-X nodes every 20 minutes on their site, in an attempt to keep traffic to the Yaasu site to a minimum we will cache the data will be refreshed in line with the Yaasu approach.

This will mean that we will only be pulling the data 72 times a day, you will be able to see the age of the data in the navigation bar on the right-hand side.

## Validity of the geolocation pins
The geolocation pins are placed on the map as the owner of the room has specfied and may not be accurate, not all owners of the rooms have provided geolocations, the map only containes entries with geolocation while the table contains all rooms that are online, in the table you can search on any fields in the data set e.g. room id or call sign. 

## About This Site
This site provides live data on active WiresX nodes, including maps and data tables. Below is a description of each link in the navigation bar:

- Home The main page of the site, providing an overview and introduction.
- Maps A page displaying a map with pins representing active WiresX nodes.
- Nodes A data table listing all active WiresX nodes with relevant details.
- JSON A link to view the data in JSON format, you could build a solution using this data.

### This project used the following components.

- Flask
- Leaflet.js
- OpenStreetMap
- Bootstrap
