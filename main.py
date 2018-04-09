import json
from math import sin, cos, sqrt, pi
from random import random

def makeCommand( x, y, debug ):
        command = {}
        command['X'] = x
        command['Y'] = y
        command['Debug'] = debug
        return command;
    
def distance( a, b ):
    return sqrt( ( a.X - b.X ) ** 2 + ( a.Y - b.Y ) ** 2 )

directionRange = {
            'TOP': [0.0, -pi],
            'TOPRIGHT': [-pi/2.0, -pi/2.0],
            'RIGHT': [-pi/2.0, -pi],
            'BOTTOMRIGHT': [-pi, -pi/2.0],
            'BOTTOM': [-pi, -pi],
            'BOTTOMLEFT': [-1.5*pi, -pi/2.0],
            'LEFT': [-1.5*pi, -pi],
            'TOPLEFT': [0.0, -pi/2.0]
        }

class GameParams:
    def __init__( self, data ):
        self.FOOD_MASS = data.get( 'FOOD_MASS' )
        self.GAME_HEIGHT = data.get( 'GAME_HEIGHT' )
        self.GAME_TICKS = data.get( 'GAME_TICKS' )
        self.GAME_WIDTH = data.get( 'GAME_WIDTH' )
        self.INERTION_FACTOR = data.get( 'INERTION_FACTOR' )
        self.MAX_FRAGS_CNT = data.get( 'MAX_FRAGS_CNT' )
        self.SPEED_FACTOR = data.get( 'SPEED_FACTOR' )
        self.TICKS_TIL_FUSION = data.get( 'TICKS_TIL_FUSION' )
        self.VIRUS_RADIUS = data.get( 'VIRUS_RADIUS' )
        self.VIRUS_SPLIT_MASS = data.get( 'VIRUS_SPLIT_MASS' )
        self.VISCOSITY = data.get( 'VISCOSITY' )
        self.FOOD_RADIUS = 2.5
        self.SPLIT_THRESHOLD = 120

class GameObject:
    def __init__( self, data ):
        self.X = data.get( 'X' )
        self.Y = data.get( 'Y' )
    
    def distance( self, other ):
        return distance( self, other )
        
class MinePart( GameObject ):
    def __init__( self, data ):
        self.X = data.get( 'X' )
        self.Y = data.get( 'Y' )
        self.Id = data.get( 'Id' )
        self.R = data.get( 'R' )
        self.M = data.get( 'M' )
        self.VX = data.get( 'SX' )
        self.VY = data.get( 'SY' )
        # таймер слияния - может отсутствовать
        if 'TTF' in data:
            self.TTF = data.get( 'TTF' ) 
        else:
            self.TTF = 0
            
class Food( GameObject ):
    pass

class Ejection( GameObject ):
    def __init__( self, data ):
        self.X = data.get( 'X' )
        self.Y = data.get( 'Y' )
        self.pId = data.get( 'pId' )
    
class Virus( GameObject ):
    def __init__( self, data ):
        self.X = data.get( 'X' )
        self.Y = data.get( 'Y' )
        self.Id = data.get( 'Id' )
        self.M = data.get( 'M' )
        self.pId = data.get( 'pId' )
        
class PlayerPart( GameObject ):
    def __init__( self, data ):
        self.X = data.get( 'X' )
        self.Y = data.get( 'Y' )
        self.Id = data.get( 'Id' )
        self.R = data.get( 'R' )
        self.M = data.get( 'M' )

class Strategy:
    
    def __init__( self ):
        self.params = None
        self.mine = []
        self.pointToMove = None
        self.food = []
        self.ejection = []
        self.virus = []
        self.player = []
        self.fieldDiameter = None
        self.minSelfRadius = None
        self.left = None
        self.right = None
        self.top = None
        self.bottom = None
        
    def parseData( self, data ):
        mine, objects = data.get( 'Mine' ), data.get( 'Objects' )
        self.mine.clear()
        self.minSelfRadius = sqrt( self.params.GAME_HEIGHT ** 2 + self.params.GAME_WIDTH ** 2 );
        self.left = self.params.GAME_WIDTH
        self.right = 0
        self.top = self.params.GAME_HEIGHT
        self.bottom = 0
        for m in mine:
            self.mine.append( MinePart( m ) )
        for m in self.mine:
            self.minSelfRadius = min( self.minSelfRadius, m.R )
            self.left = min( self.left, m.X - m.R )
            self.right = max( self.right, m.X + m.R )
            self.top = min( self.top, m.Y - m.R )
            self.bottom = max( self.bottom, m.Y + m.R )
        self.food.clear()
        self.ejection.clear()
        self.virus.clear()
        self.player.clear()
        for o in objects:
            objectType = o.get( 'T' )
            if objectType == 'F':
                self.food.append( Food( o ) )
            elif objectType == 'E':
                self.ejection.append( Ejection( o ) )
            elif objectType == 'V':
                self.virus.append( Virus( o ) )
            elif objectType == 'P':
                self.player.append( PlayerPart( o ) )
            
    def run( self ):
        self.params = GameParams( json.loads( input() ) )
        self.fieldDiameter = sqrt( self.params.GAME_WIDTH ** 2 + self.params.GAME_HEIGHT ** 2 )
        while True:
            data = json.loads( input() )
            cmd = self.on_tick( data )
            print( json.dumps(cmd) )

    def isFoodReachable( self, food ):
        effectiveRadius = self.minSelfRadius - self.params.FOOD_RADIUS / 6
        # для угла (0, 0)
        if food.X < self.minSelfRadius and food.Y < self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.minSelfRadius, 'Y': self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X > self.params.GAME_WIDTH - self.minSelfRadius and food.Y < self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.params.GAME_WIDTH - self.minSelfRadius, 'Y': self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X < self.minSelfRadius and food.Y > self.params.GAME_HEIGHT - self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.minSelfRadius, 'Y': self.params.GAME_HEIGHT - self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X > self.params.GAME_WIDTH - self.minSelfRadius and food.Y > self.params.GAME_HEIGHT - self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.params.GAME_WIDTH - self.minSelfRadius, 'Y': self.params.GAME_HEIGHT - self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        else:
            return food.X > ( self.params.FOOD_RADIUS / 6 ) and food.X < ( self.params.GAME_WIDTH - self.params.FOOD_RADIUS / 6 ) and food.Y > ( self.params.FOOD_RADIUS / 6 ) and food.Y < ( self.params.GAME_HEIGHT - self.params.FOOD_RADIUS / 6 )
        
        
    def get_nearest_food( self ):
        nearest = None
        minDist = self.fieldDiameter
        for food in self.food:
            if not self.isFoodReachable( food ):
                continue
            for m in self.mine:
                dist = m.distance( food )
                if dist < minDist:
                    minDist = dist
                    nearest = food
        return nearest
    
    def getBorderKey( self ):
        borderKey = ''
        if self.top <= 0:
            borderKey += 'TOP'
        elif self.bottom >= self.params.GAME_HEIGHT:
            borderKey += 'BOTTOM'
        if self.left <= 0:
            borderKey += 'LEFT'
        elif self.right >= self.params.GAME_WIDTH:
            borderKey += 'RIGHT'
        return borderKey
    
    def isOnBorder( self ):
        return self.top <= 0 or self.bottom >= self.params.GAME_HEIGHT or self.left <= 0 or self.right >= self.params.GAME_WIDTH
    
    def distance( self, obj ):
        distance = sqrt( self.params.GAME_WIDTH ** 2 + self.params.GAME_HEIGHT ** 2 )
        for m in self.mine:
            distance = min( distance, m.distance( obj ) )
        return distance
            
    def getNewPointToMove( self ):
        x = self.minSelfRadius + random() * ( self.params.GAME_WIDTH - self.minSelfRadius * 2 )
        y = self.minSelfRadius + random() * ( self.params.GAME_HEIGHT - self.minSelfRadius * 2 )
        point = GameObject( { 'X': x, 'Y': y } )
        while self.distance( point ) <= self.minSelfRadius:
            x = self.minSelfRadius + random() * ( self.params.GAME_WIDTH - self.minSelfRadius * 2 )
            y = self.minSelfRadius + random() * ( self.params.GAME_HEIGHT - self.minSelfRadius * 2 )
            point = GameObject( { 'X': x, 'Y': y } )
        return point
    
    def on_tick( self, data ):
        self.parseData( data )
        command = {}
        if len( self.mine ) == 0:
            command = makeCommand( 0, 0, 'game over' )
        else:
            # избегаем опасные соседей
            # пытаемся съесть конкурента если можем
            food = self.get_nearest_food()
            if food:
                # пытаемся съесть еду если видно
                command = makeCommand( food.X, food.Y, 'to food' )
            else:
                # движемся к выбранной точке
                if self.pointToMove is None or self.distance( self.pointToMove ) <= self.minSelfRadius:
                    self.pointToMove = self.getNewPointToMove()
                command = makeCommand( self.pointToMove.X, self.pointToMove.Y, 'to point' )
        # нужно скорректировать для случая близости к границе
        return command

if __name__ == '__main__':
    s = Strategy()
    s.run()