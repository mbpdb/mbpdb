r"""
Make codecs for fixed size structured chunks serialization and deserialization of
sequences, tabular data, and time-series.

The easiest and bigest bang for your buck is ``mk_codec``

>>> from recode import mk_codec
>>> encoder, decoder = mk_codec()

``encoder`` will encode a list (or any iterable) of numbers into bytes

>>> b = encoder([0, -3, 3.14])
>>> b
b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xc0\x1f\x85\xebQ\xb8\x1e\t@'

``decoder`` will decode those bytes to get you back your numbers

>>> decoder(b)
[0.0, -3.0, 3.14]

There's only really one argument you need to know about in ``mk_codec``.
The first argument, called `chk_format`, which is a string of characters from
the "Format" column of
https://docs.python.org/3/library/struct.html#format-characters

The length of the string specifies the number of "channels",
and each individual character of the string specifies the kind of encoding you should
apply to each "channel" (hold your horses, we'll explain).

The one we've just been through is in fact

>>> encoder, decoder = mk_codec('d')

That is, it will expect that your data is a list of numbers, and they'll be encoded
with the 'd' format character, that is 8-bytes doubles.
That default is goo because it gives you a lot of room, but if you knew that you
would only be dealing with 2-byte integers (as in most WAV audio waveforms),
you would have chosen `h`:

>>> encoder, decoder = mk_codec('h')

What about those channels?
Well, some times you need to encode/decode multi-channel streams, such as:

>>> multi_channel_stream = [[3, -1], [4, -1], [5, -9]]

Say, for example, if you were dealing with stereo waveform
(with the standard PCM_16 format), you'd do it this way:

>>> encoder, decoder = mk_codec('hh')
>>> pcm_bytes = encoder(iter(multi_channel_stream))
>>> pcm_bytes
b'\x03\x00\xff\xff\x04\x00\xff\xff\x05\x00\xf7\xff'
>>> decoder(pcm_bytes)
[(3, -1), (4, -1), (5, -9)]


The `n_channels` and `chk_size_bytes` arguments are there if you want to assert
that your number of channels and chunk size are what you expect.
Again, these are just for verification, because we know how easy it is to
misspecify the `chk_format`, and how hard it can be to notice that we did.

It is advised to use these in any production code, for the sanity of everyone!

>>> mk_codec('hhh', n_channels=2)
Traceback (most recent call last):
  ...
AssertionError: You said there'd be 2 channels, but I inferred 3
>>> mk_codec('hhh', chk_size_bytes=3)
Traceback (most recent call last):
  ...
AssertionError: The given chk_size_bytes 3 did not match the inferred (from chk_format) 6

Finally, so far we've done it this way:

>>> encoder, decoder = mk_codec('hHifd')

But see that what's actually returned is a NAMED tuple, which means that you can
can also get one object that will have `.encode` and `.decode` properties:

>>> codec = mk_codec('hHifd')
>>> to_encode = [[1, 2, 3, 4, 5], [6, 7, 8, 9, 10]]
>>> encoded = codec.encode(to_encode)
>>> decoded = codec.decode(encoded)
>>> decoded
[(1, 2, 3, 4.0, 5.0), (6, 7, 8, 9.0, 10.0)]

And you can checkout the properties of your encoder and decoder (they
should be the same)

>>> codec.encode.chk_format
'hHifd'
>>> codec.encode.n_channels
5
>>> codec.encode.chk_size_bytes
24

"""
from recode.base import mk_codec  # main interface function

mk_codec = mk_codec

from recode.util import spy, get_struct, list_of_dicts
from recode.base import *

from recode.audio import (
    # encode_wav_bytes,  # commented out because doesn't work
    # ... see https://github.com/otosense/recode/issues/3
    decode_wav_bytes,
    encode_wav_header_bytes,
    decode_wav_header_bytes,
    mk_pcm_audio_codec,
    encode_pcm_bytes,
    decode_pcm_bytes,
)
