### Format 

```markdown
### [Name](URL)

- Type: (CSV, JSON, etc)
- Object URLS: (True/ False)
- Image URLS: (True/ False)
- Notes: 


```


### [Tate Gallery](https://github.com/tategallery/collection) 

- Type: CSV
- Object URLS: True 
- Image URLS: True (with processing)
- Notes:
  - 10 years out of date 
  - High quality image urls are not included by default, but thumbnail URLs are (but they're slightly wrong). Here's what to do:
    - Thumbnail URLs included are formatted like: http://www.tate.org.uk/art/images/work/D/D13/D13283_8.jpg
    - However they need to be: http://media.tate.org.uk/art/images/work/D/D13/D13283_8.jpg
    - And then to get the high quality image: http://media.tate.org.uk/art/images/work/D/D13/D13283_10.jpg
  - _Also note that their repo contains a nice list of things people have built with the data_

### [Cooper Hewitt, Smithsonian Design Museum](https://github.com/cooperhewitt/collection)

- Type: JSON, but spread across lots of files
- Object URLS: 
- Image URLS:
- Notes:
  - Its another strange spread across lots of JSON files. Need to come back to this one later.

### [The National Gallery of Art (DC)](https://github.com/NationalGalleryOfArt/opendata)

- Type: CSV
- Object URLS: False
- Image URLS: False
- Notes:
  - No URLS at all in the dataset, but I'm sure I can find a way to get them.  
  - They have an API: https://api.nga.gov/

### [Minneapolis Institute of Art](https://github.com/artsmia/collection)

- Type: JSON, but spread across lots of files

### [The Metropolitan Museum of Art](https://github.com/metmuseum/openaccess/tree/master)

- Type: CSV
- Object URLS: True
- Image URLS: 
- Notes:
    - _Doesn't include image URLs in the dataset..._ I'm sure I can find a way to get them (legally lol), just move on 
    for now and come back later! Get the 90% solution first!
    - Note: there's an API: https://metmuseum.github.io/