from utils import console

def getAll(pageable_function, nPageSize = 200, **kwargs):
    allEntities = dict()

    nPageNumber = 1
    nPageCount = 1
    while nPageNumber <= nPageCount:
        api_response = pageable_function(page_size=nPageSize, page_number=nPageNumber, **kwargs)
        console.info('Read %s entities' % len(api_response.entities))
        for entity in api_response.entities:
            allEntities[entity.name] = entity
            
        nPageCount = api_response.page_count if api_response.page_count else 1
        nPageNumber += 1
        
    console.info('Read total %s entities' % len(allEntities))
    return allEntities

def getAllById(pageable_function, nPageSize = 200, **kwargs):
    allEntities = dict()

    nPageNumber = 1
    nPageCount = 1
    while nPageNumber <= nPageCount:
        api_response = pageable_function(page_size=nPageSize, page_number=nPageNumber, **kwargs)
        console.info('Read %s entities' % len(api_response.entities))
        for entity in api_response.entities:
            allEntities[entity.id] = entity
            
        nPageCount = api_response.page_count if api_response.page_count else 1
        nPageNumber += 1
        
    console.info('Read total %s entities' % len(allEntities))
    return allEntities

def getByName(pageable_function, name):
    entity = None

    api_response = pageable_function(name=name)
    if api_response.total == 1:
        entity = api_response.entities[0]
    elif api_response.total > 1:
        for e in api_response.entities:
            if e.name == name:
                entity = e
                break
    
    return entity
