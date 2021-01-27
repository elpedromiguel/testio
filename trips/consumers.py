from channels.generic.websocket import AsyncJsonWebsocketConsumer
from channels.db import database_sync_to_async

from trips.serializers import NestedTripSerializer, TripSerializer 

from trips.models import Trip

class TaxiConsumer(AsyncJsonWebsocketConsumer):
    groups = ['test'] # new

    @database_sync_to_async
    def _create_trip(self, data):
        serializer = TripSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.create(serializer.validated_data)

    @database_sync_to_async
    def _update_trip(self, data):
        instance = Trip.objects.get(id=data.get('id'))
        serializer = TripSerializer(data=data)
        serializer.is_valid(raise_exception=True)
        return serializer.update(instance, serializer.validated_data)

    @database_sync_to_async
    def _get_trip_data(self, trip):
        return NestedTripSerializer(trip).data

    @database_sync_to_async
    def _get_user_group(self, user):
        return user.groups.first().name

    @database_sync_to_async
    def _get_trip_ids(self, user):
        user_groups = user.groups.values_list('name', flat=True)
        if 'driver' in user_groups:
            trip_ids = user.trips_as_driver.exclude(
                status=Trip.COMPLETED
            ).only('id').values_list('id', flat=True)
        else:
            trip_ids = user.trips_as_rider.exclude(
                status=Trip.COMPLETED
            ).only('id').values_list('id', flat=True)
        return map(str, trip_ids)

    async def connect(self):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
        else:
            user_group = await self._get_user_group(user)
            if user_group == 'driver':
                await self.channel_layer.group_add(
                    group='drivers',
                    channel=self.channel_name
                )

            for trip_id in await self._get_trip_ids(user):
                await self.channel_layer.group_add(
                    group=trip_id,
                    channel=self.channel_name
                )

            await self.accept()

    async def create_trip(self, message):
        data = message.get('data')
        trip = await self._create_trip(data)
        trip_data = await self._get_trip_data(trip)

        await self.channel_layer.group_send(group='drivers', message={
            'type': 'echo.message',
            'data': trip_data
        })

        await self.channel_layer.group_add(
            group=f'{trip.id}',
            channel=self.channel_name
        )
        await self.send_json({
          'type': 'echo.message',
          'data': trip_data,
        })

    async def disconnect(self, code):
        user = self.scope['user']
        if user.is_anonymous:
            await self.close()
        else:
            user_group = await self._get_user_group(user)
            if user_group == 'driver':
                await self.channel_layer.group_discard(
                    group='drivers',
                    channel=self.channel_name
                )
        await super().disconnect(code)

    async def echo_message(self, message):
        await self.send_json(message)

    async def receive_json(self, content, **kwargs):
        message_type = content.get('type')
        if message_type == 'create.trip':
            await self.create_trip(content)
        elif message_type == 'echo.message':
            await self.echo_message(content)
        elif message_type == 'update.trip':
            await self.update_trip(content)

    async def update_trip(self, message):
        data = message.get('data')
        trip = await self._update_trip(data)
        trip_id = f'{trip.id}'
        trip_data = await self._get_trip_data(trip)

        # Send update to rider.
        await self.channel_layer.group_send(
            group=trip_id,
            message={
                'type': 'echo.message',
                'data': trip_data,
            }
        )

        # Add driver to the trip group.
        await self.channel_layer.group_add(
            group=trip_id,
            channel=self.channel_name
        )

        await self.send_json({
            'type': 'echo.message',
            'data': trip_data
        })

    #test11
    async def test_driver_join_trip_group_on_connect(self, settings):
        settings.CHANNEL_LAYERS = TEST_CHANNEL_LAYERS
        user, access = await create_user(
            'test.user@example.com', 'pAssw0rd', 'driver'
        )
        trip = await create_trip(driver=user)
        communicator = WebsocketCommunicator(
            application=application,
            path=f'/taxi/?token={access}'
        )
        connected, _ = await communicator.connect()

        # Send a message to the trip group.
        message = {
            'type': 'echo.message',
            'data': 'This is a test message. Test 10',
        }
        channel_layer = get_channel_layer()
        await channel_layer.group_send(f'{trip.id}', message=message)

        # Rider receives message.
        response = await communicator.receive_json_from()
        assert response == message

        await communicator.disconnect()