"""Base recode objects"""


from dataclasses import dataclass
from typing import Iterable, Callable, Sequence, Union, Any
from struct import pack, unpack, iter_unpack
import struct
from operator import itemgetter, attrgetter
from collections import namedtuple
from recode.util import spy, get_struct, list_of_dicts


Meta = Sequence[bytes]
Chunk = Sequence[bytes]
Chunks = Iterable[Chunk]
ByteChunker = Callable[[bytes], Chunks]
Sample = Any  # but usually a number
Frame = Union[Sample, Sequence[Sample]]
Frames = Iterable[Frame]

Encoder = Callable[[Frames], bytes]
Decoder = Callable[[bytes], Iterable[Frame]]

ChunkToFrame = Callable[[Chunk], Frame]
FrameToChunk = Callable[[Frame], Chunk]

MetaToFrame = Callable[[Meta], Frame]
FrameToMeta = Callable[[Frame], Meta]

DFLT_CHK_FORMAT = 'd'

codec_tuple = namedtuple('codec_tuple', field_names='encode decode')


def mk_codec(
    chk_format: str = DFLT_CHK_FORMAT,
    n_channels: int = None,
    chk_size_bytes: int = None,
):
    r"""
    Enable the definition of codec specs based on `chk_format`,
    format characters of the python struct module
    (https://docs.python.org/3/library/struct.html#format-characters)

    :param chk_format: The format of a chunk, as specified by the struct module
        The length of the string specifies the number of "channels",
        and each individual character of the string specifies the kind of encoding
        you should apply to each "channel" (hold your horses, we'll explain).
        See https://docs.python.org/3/library/struct.html#format-characters
    :param n_channels: Expected of channels. If given, will assert that the
        number of channels expressed by the `chk_format` is indeed what is expected.
        the number of channels expressed by the `chk_format`.
    :param chk_size_bytes: Expected number of bytes per chunk.
        If given, will assert that the chunk size expressed by the `chk_format` is
        indeed the one expected.

    :return: A (named)tuple with encode and decode functions

    The easiest and bigest bang for your buck is ``mk_codec``

    >>> from recode import mk_codec
    >>> encoder, decoder = mk_codec()
    >>> b = encoder([0, -3, 3.14])
    >>> b
    b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xc0\x1f\x85\xebQ\xb8\x1e\t@'
    >>> decoder(b)
    [0.0, -3.0, 3.14]

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
    specs = StructCodecSpecs(chk_format, n_channels, chk_size_bytes)
    encoder = ChunkedEncoder(frame_to_chk=specs.frame_to_chk)
    add_coding_attributes(encoder, specs)
    decoder = ChunkedDecoder(chk_to_frame=specs.chk_to_frame)
    add_coding_attributes(decoder, specs)
    codec = codec_tuple(encoder, decoder)
    # add_coding_attributes(codec, specs)
    return codec


mk_encoder_and_decoder = mk_codec  # backcompat alias


def add_coding_attributes(to_obj, from_obj):
    to_obj.chk_format = from_obj.chk_format
    to_obj.n_channels = from_obj.n_channels
    to_obj.chk_size_bytes = from_obj.chk_size_bytes


@dataclass
class ChunkedEncoder(Encoder):
    """
    Serializes numerical streams and sequences
    """

    frame_to_chk: FrameToChunk
    chk_format = None
    n_channels = None
    chk_size_bytes = None

    def __call__(self, frames: Frames):
        return b''.join(map(self.frame_to_chk, frames))

    def __eq__(self, other):
        return self.chk_format == other.chk_format


@dataclass
class MetaEncoder(Encoder):
    """
    Serializes tabular data (must be formatted as list of dicts)
    """

    frame_to_chk: FrameToChunk
    frame_to_meta: FrameToMeta

    def __call__(self, frames: Frames):
        meta = self.frame_to_meta(frames)
        vals = list(map(list, (d.values() for d in frames)))
        if len(vals[0]) == 1:
            vals = [item for sublist in vals for item in sublist]
        return meta + b''.join(map(self.frame_to_chk, vals))


first_element = itemgetter(0)  # "equivalent" to lambda x: x[0]


@dataclass
class ChunkedDecoder(Decoder):
    """
    Deserializes numerical streams and sequences serialized by ChunkedEncoder
    """

    chk_to_frame: ChunkToFrame
    chk_format = None
    n_channels = None
    chk_size_bytes = None

    def __call__(self, b: bytes):
        iterator = self.chk_to_frame(b)
        frame = list(iterator)
        if len(frame[0]) == 1:
            frame = [item for tup in frame for item in tup]
        return frame

    def __eq__(self, other):
        return self.chk_format == getattr(other, 'chk_format', None)


@dataclass
class IterativeDecoder(Decoder):
    """
    Creates an iterator of deserialized chunks of numerical streams and sequences serialized
    by ChunkedEncoder
    """

    chk_to_frame: ChunkToFrame

    def __call__(self, b: bytes):
        iterator = self.chk_to_frame(b)
        return iterator


@dataclass
class MetaDecoder(Decoder):
    """
    Deserializes tabular data serialized by MetaEncoder
    """

    chk_to_frame: ChunkToFrame
    meta_to_frame: MetaToFrame

    def __call__(self, b: bytes):
        cols, split = self.meta_to_frame(b)
        b = b[split:]
        vals = self.chk_to_frame(b)
        return list_of_dicts(cols, vals)


def _split_chk_format(chk_format: str = DFLT_CHK_FORMAT):
    """
    Splits a struct format string into the byte order character and format characters
    >>> assert _split_chk_format('hq') == ('', 'hq')
    >>> assert _split_chk_format('@hq') == ('@', 'hq')
    """
    if chk_format[0] in '@=<>!':
        return chk_format[0], chk_format[1:]
    return '', chk_format


def _format_chars_part_of_chk_format(chk_format: str = DFLT_CHK_FORMAT):
    """
    Returns the format character part of a struct format string
    >>> assert _format_chars_part_of_chk_format('!hh') == 'hh'
    >>> _format_chars_part_of_chk_format('q')
    'q'
    """
    byte_order, format_chars = _split_chk_format(chk_format)
    return format_chars


def _chk_format_to_n_channels(chk_format: str = DFLT_CHK_FORMAT):
    """
    Returns the number of channels defined a struct format string
    >>> assert _chk_format_to_n_channels('hq') == 2
    >>> _chk_format_to_n_channels('@hqt')
    3
    """
    return len(_format_chars_part_of_chk_format(chk_format))


def _chk_format_is_for_single_channel(chk_format: str = DFLT_CHK_FORMAT):
    """
    Returns if a struct format string is designated for a single channel of data
    >>> assert _chk_format_is_for_single_channel('h') == True
    >>> assert _chk_format_is_for_single_channel('@hq') == False
    """
    return _chk_format_to_n_channels(chk_format) == 1


def frame_to_meta(frame):
    r"""
    Defines header for serialization of tabluar data
    >>> rows = [{'customer': 1}, {'customer': 2}, {'customer': 3}]
    >>> assert frame_to_meta(rows) == b'\x08\x00customer'
    """
    cols = list(frame[0].keys())
    s = '.'.join(cols)
    return b'' + pack('h', len(s)) + s.encode()


def meta_to_frame(meta):
    r"""
    Deserializes header for deserialization of tabular data
    >>> meta = b'\x1c\x00customer.apple.banana.tomato\x01\x00\x01\x00\x02\x00\x03\x00\x02\x00\
    ... x03\x00\x02\x00\x05\x00\x01\x00\x03\x00\x04\x00\t\x00'
    >>> assert meta_to_frame(meta)[0] == ['customer', 'apple', 'banana', 'tomato']
    """
    length = unpack('h', meta[:2])[0] + 2
    cols = (meta[2:length]).decode().split('.')
    return cols, length


@dataclass
class StructCodecSpecs:
    r"""Enable the definition of codec specs based on format characters of the
    python struct module
    (https://docs.python.org/3/library/struct.html#format-characters)

    :param chk_format: The format of a chunk, as specified by the struct module
        The length of the string specifies the number of "channels",
        and each individual character of the string specifies the kind of encoding
        you should apply to each "channel" (hold your horses, we'll explain).
        See https://docs.python.org/3/library/struct.html#format-characters
    :param n_channels: Expected of channels. If given, will assert that the
        number of channels expressed by the `chk_format` is indeed what is expected.
        the number of channels expressed by the `chk_format`.
    :param chk_size_bytes: Expected number of bytes per chunk.
        If given, will assert that the chunk size expressed by the `chk_format` is
        indeed the one expected.

    Note: All encoder/decoder (codec) specs can be expressed though the `chk_format`.
    Yet, though `n_channels` and `chk_size_bytes` are both optional, it is advised to
    include them in production code since they act as extra confirmation of the codec
    to be used. Encoding and decoding problems can be hard to notice until much
    later on downstream, and are therefore hard to debug.

    To utilise recode, first define your codec specs. If your frame is only one channel
    (ex. a list) then your format string will include two characters,
    a byte character (@, =, <, >, !) and a format character. The format character
    should match the data type of the samples in the frame so they are properly
    encoded/decoded. This can be seen in thefollowing example.

    >>> specs = StructCodecSpecs(chk_format='h')
    >>> print(specs)
    StructCodecSpecs(chk_format='h', n_channels=1, chk_size_bytes=2)
    >>> encoder = ChunkedEncoder(frame_to_chk=specs.frame_to_chk)
    >>> decoder = ChunkedDecoder(chk_to_frame=specs.chk_to_frame)
    >>> frames = [1, 2, 3]
    >>> b = encoder(frames)
    >>> assert b == b'\x01\x00\x02\x00\x03\x00'
    >>> decoded_frames = list(decoder(b))
    >>> assert decoded_frames == frames

    The only reason (but it's a good one) to specify `n_channels` is to assert them.

    >>> specs = StructCodecSpecs(chk_format='@hh', n_channels=2)
    >>> print(specs)
    StructCodecSpecs(chk_format='@hh', n_channels=2, chk_size_bytes=4)
    >>> encoder = ChunkedEncoder(frame_to_chk=specs.frame_to_chk)
    >>> decoder = ChunkedDecoder(chk_to_frame=specs.chk_to_frame)
    >>> frames = [(1, 2), (3, 4), (5, 6)]
    >>> b = encoder(frames)
    >>> assert b == b'\x01\x00\x02\x00\x03\x00\x04\x00\x05\x00\x06\x00'
    >>> decoded_frames = list(decoder(b))
    >>> assert decoded_frames == frames

    On the other hand, if each channel has a different data type, say (int, float, int),
    then your format string needs a format character for each of your channels.
    This can be seen in the following example, which also shows the use
    of a different byte character (=).

    >>> specs = StructCodecSpecs(chk_format = '=hdh')
    >>> print(specs)
    StructCodecSpecs(chk_format='=hdh', n_channels=3, chk_size_bytes=12)
    >>> encoder = ChunkedEncoder(frame_to_chk = specs.frame_to_chk)
    >>> decoder = ChunkedDecoder(chk_to_frame=specs.chk_to_frame)
    >>> frames = [(1, 2.45, 1), (3, 4.321, 3)]
    >>> b = encoder(frames)
    >>> assert b == b'\x01\x00\x9a\x99\x99\x99\x99\x99\x03@\x01\x00\x03\x00b\x10X9\xb4H\x11@\x03\x00'
    >>> decoded_frames = list(decoder(b))
    >>> assert decoded_frames == frames

    Along with a ChunkedDecoder, you can also use an IterativeDecoder which implements
    the struct.iter_unpack function.
    IterativeDecoder only requires one argument, a chk_to_frame_iter function,
    and returns an iterator of each chunk.
    An example of an IterativeDecorator can be seen below.

    >>> specs = StructCodecSpecs(chk_format = 'hdhd')
    >>> print(specs)
    StructCodecSpecs(chk_format='hdhd', n_channels=4, chk_size_bytes=32)
    >>> encoder = ChunkedEncoder(frame_to_chk = specs.frame_to_chk)
    >>> decoder = IterativeDecoder(chk_to_frame = specs.chk_to_frame)
    >>> frames = [(1,1.1,1,1.1),(2,2.2,2,2.2),(3,3.3,3,3.3)]
    >>> b = encoder(frames)
    >>> iter_frames = decoder(b)
    >>> assert next(iter_frames) == frames[0]
    >>> next(iter_frames)
    (2, 2.2, 2, 2.2)

    Along with using recode for the kinds of data we have looked at so far,
    it can also be applied to DataFrames when
    they have been converted to a list of dicts using MetaEncoder and MetaDecoder.
    An example of this can be seen below.

    >>> data = [{'foo': 1.1, 'bar': 2.2},
    ...         {'foo': 513.23, 'bar': 456.1},
    ...         {'foo': 32.0, 'bar': 6.7}]
    >>> specs = StructCodecSpecs(chk_format='dd')
    >>> print(specs)
    StructCodecSpecs(chk_format='dd', n_channels=2, chk_size_bytes=16)
    >>> encoder = MetaEncoder(frame_to_chk = specs.frame_to_chk, frame_to_meta = frame_to_meta)
    >>> decoder = MetaDecoder(chk_to_frame = specs.chk_to_frame, meta_to_frame = meta_to_frame)
    >>> b = encoder(data)
    >>> assert decoder(b) == data
    """
    chk_format: str = DFLT_CHK_FORMAT
    n_channels: int = None
    chk_size_bytes: int = None

    def __post_init__(self):
        inferred_n_channels = _chk_format_to_n_channels(self.chk_format)
        if self.n_channels is None:
            self.n_channels = inferred_n_channels
        else:
            assert self.n_channels == inferred_n_channels, (
                f"You said there'd be {self.n_channels} channels, "
                f'but I inferred {inferred_n_channels}'
            )

        chk_size_bytes = struct.calcsize(self.chk_format)
        if self.chk_size_bytes is None:
            self.chk_size_bytes = chk_size_bytes
        else:
            assert self.chk_size_bytes == chk_size_bytes, (
                f'The given chk_size_bytes {self.chk_size_bytes} did not match the '
                f'inferred (from chk_format) {chk_size_bytes}'
            )

    def frame_to_chk(self, frame):
        if self.n_channels == 1:
            return pack(self.chk_format, frame)
        else:
            return pack(self.chk_format, *frame)

    def chk_to_frame(self, chk):
        return iter_unpack(self.chk_format, chk)

    def __eq__(self, other):
        return self.chk_format == other.chk_format


def specs_from_frames(frames: Frames):
    r"""
    Implicitly defines the codec specs based on the frames to encode/decode.
    specs_from_frames returns a tuple of an iterator of frames and the defined StructCodecSpecs. If frames is an
    iterable, then the iterator can be ignored like the following example.
    >>> frames = [1,2,3]
    >>> _, specs = specs_from_frames(frames)
    >>> print(specs)
    StructCodecSpecs(chk_format='h', n_channels=1, chk_size_bytes=2)
    >>> encoder = ChunkedEncoder(frame_to_chk = specs.frame_to_chk)
    >>> decoder = ChunkedDecoder(chk_to_frame=specs.chk_to_frame)
    >>> b = encoder(frames)
    >>> assert b == b'\x01\x00\x02\x00\x03\x00'
    >>> decoded_frames = list(decoder(b))
    >>> assert decoded_frames == frames

    If frames is an iterator, then we can still use specs_from_frames as long as we redefine frames from the output like
    in the following example.

    >>> frames = iter([[1.1,2.2],[3.3,4.4]])
    >>> frames, specs = specs_from_frames(frames)
    >>> print(specs)
    StructCodecSpecs(chk_format='dd', n_channels=2, chk_size_bytes=16)
    >>> encoder = ChunkedEncoder(frame_to_chk = specs.frame_to_chk)
    >>> decoder = ChunkedDecoder(chk_to_frame=specs.chk_to_frame)
    >>> b = encoder(frames)
    >>> decoded_frames = list(decoder(b))
    >>> assert decoded_frames == [(1.1,2.2),(3.3,4.4)]
    """
    head, frames = spy(frames)

    if isinstance(head[0], (int, float)):
        format_char = get_struct(type(head[0]))
        n_channels = 1
    elif isinstance(head[0], (list, tuple)):
        format_char = get_struct(type(head[0][0]))
        n_channels = len(head[0])
    elif isinstance(head[0], dict):
        format_char = get_struct(type(list(head[0].values())[0]))
        n_channels = len(head[0].keys())
    else:
        raise AttributeError('Unknown data format')

    if n_channels is not None:
        format_char = format_char * n_channels
    return frames, StructCodecSpecs(format_char, n_channels=n_channels)
