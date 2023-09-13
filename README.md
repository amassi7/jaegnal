# Jaegnal
Built as the final project for CSCI 339: Distributed Systems.

A distributed P2P minimal messaging app that uses the Chord protocol for the Distributed Hash Table (DHT).

So far, tested for only two clients (users), and works just fine.

Changed the code a bit to use exclusively local addresses.

Handled sockets/message transmission manually, thinking of changing that.

To do: test for more than two users and revise Chord. Streamline testing.

# To use:
Run the server script and specify a port. Then run the clients and specify the server port to connect to. (The idea is that the server would initiate clients into the network then cut off the connection-- the Chord network is meant to be entirely P2P)