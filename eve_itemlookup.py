import discord
import aiohttp
import configparser


class MyClient(discord.Client):
    def __init__(self): # constructor for when we declare an instance of a class. All variables declared here are available to all functions inside the class
        super().__init__()
        self.cache_dogma = {} # dict for caching requests for attribute id

    async def on_ready(self):
        print('Logged in as')
        print(self.user.name)
        print(self.user.id)
        print('------')

    async def get_dogma_names(self, dogma_list):
        """given a list of dictionaries consisting of dogma ids, make a new list with ids changed to names"""
        try:
            return_list = []
            for d in dogma_list:
                cache = self.cache_dogma.get(d.get('attribute_id'))
                if cache is None:
                    async with aiohttp.request('GET', 'https://esi.evetech.net/latest/dogma/attributes/{}'.format(d.get('attribute_id'))) as response:
                        if response.status == 200:
                            result: dict = await response.json()  # convert response to json data to a dictionary
                            if result.get('display_name') is not None:
                                return_list.append({'name': result.get('display_name'), 'value': d.get('value')})
                                self.cache_dogma[d.get('attribute_id')] = result
                                print("Downloaded dogma attribute: {}".format(result))
                        else:
                            print('Error: {} code response when requesting data from ESI.'.format(response.status))
                            return None
                else:
                    return_list.append({'name': cache.get('display_name'), 'value': d.get('value')})
            return return_list  # return the list of newly resolved names if everything resolved
        except Exception as ex:
            print(ex)
            return None

    async def get_type_dogma_attributes(self, type_id):
        """given a type_id return a list of attribute ids and values. returns None on error or not found. returns a list of dicts otherwise"""
        try:
            async with aiohttp.request('GET', 'https://esi.evetech.net/latest/universe/types/{}'.format(type_id)) as response:
                if response.status == 200:
                    result: dict = await response.json()  # convert response to json data to a dictionary
                    if result.get('dogma_attributes') is not None:
                        return result.get('dogma_attributes')  # returns a list of dictionaries
                    else:
                        return None
                else:
                    print('Error: {} code response when requesting data from ESI.'.format(response.status))
                    return None
        except Exception as ex:
            print(ex)
            return None

    async def get_type_id(self, lookup_request):
        """returns an integer for the given lookup. returns None if the object was not found or an error occurred"""
        p = {'categories': 'inventory_type', 'strict': 'true', 'search': lookup_request}
        try:
            async with aiohttp.request('GET','https://esi.evetech.net/latest/search', params=p) as response:
                if response.status == 200:
                    result: dict = await response.json()  # convert response to json data to a dictionary
                    if result.get('inventory_type') is not None:
                        return result.get('inventory_type')[0]
                    else:
                        return None
                else:
                    print('Error: {} code response when requesting data from ESI.'.format(response.status))
                    return None
        except Exception as ex:
            print(ex)
            return None

    async def command_lookup(self, lookup_request):
        """this function takes a lookup string and returns string to be posted to a discord channel"""
        type_id = await self.get_type_id(lookup_request)
        if type_id is None:
            return "An error occurred when searching for {} or the item was not found.".format(lookup_request)
        dogma = await self.get_type_dogma_attributes(type_id)
        if dogma is None:
            return "An error occurred when requesting dogma for type id: {}.".format(type_id)
        resolved_attribute_names = await self.get_dogma_names(dogma)
        if resolved_attribute_names is None:
            return "An error occurred when querying attribute for type_id {}.".format(type_id)
        e = discord.Embed()
        e.color = discord.Colour(0x265c58)
        e.set_author(name='Item Lookup: {}'.format(lookup_request))
        e.set_thumbnail(url="https://imageserver.eveonline.com/Type/{}_64.png".format(type_id))
        attribute_string = ""
        for attribute in resolved_attribute_names:
            attribute_string += "{} : {}\n".format(str(attribute.get('name')), str(attribute.get('value')))
            if len(attribute_string) >= 900:
                e.add_field(name="Attributes", value=attribute_string)
                attribute_string = ""
        if len(attribute_string) != 0:
            e.add_field(name="Attributes", value=attribute_string)
        return e

    async def on_message(self, message):
        # we do not want the bot to reply to itself
        if message.author.id == self.user.id:
            return
        if message.content.startswith('ML! Help'):
            await message.channel.send('Type ML! "exact item name" to pull up info on an item or ship') 
        elif message.content.startswith('ML!'):
            await message.channel.send('Hello {0.author.mention}'.format(message)) 
        elif message.content.startswith('ML!'):
            str_item_only = (message.content.split(None, 1)[1]).strip()  # split the command so that we only retrieve content after command and remove all trailing and leading white space
            response = await self.command_lookup(str_item_only)  # run our lookup command on the given input item
            if isinstance(response, discord.Embed):
                await message.channel.send(embed=response)  # send our response to the discord channel
            else:
                await message.channel.send(response)
        else:
            pass  # do nothing


config = configparser.ConfigParser()
config.read('config.ini')
client = MyClient()
client.run(config.get(section='Discord', option='token'))
